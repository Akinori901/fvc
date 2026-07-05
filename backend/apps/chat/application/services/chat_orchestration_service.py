"""Function Calling ループの司令塔。

LLM → ツール呼び出し → ツール結果送り返し → 最終応答 までを
MAX_ITER 回までに制限して回す。

ループ中に生成された全てのメッセージ（user / assistant / tool）を
順序付きで返却し、呼び出し側（SendChatMessageUseCase）が永続化する。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from apps.chat.domain.entities import ChatMessageEntity
from apps.chat.domain.exceptions import ChatToolInvocationError

if TYPE_CHECKING:
    from apps.chat.domain.llm_client import AbstractLlmClient
    from apps.mcp.application.services.tool_invocation_service import ToolInvocationService

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ITER = 5


@dataclass
class OrchestrationResult:
    """Function Calling ループ全体の結果。"""

    session_id: int
    new_messages: list[ChatMessageEntity] = field(default_factory=list)
    final_assistant_content: str = ""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    iterations: int = 0
    truncated: bool = False  # MAX_ITER に到達して打ち切ったか
    model_used: str = ""
    provider: str = ""


class ChatOrchestrationService:
    """Function Calling ループの実行を担うサービス。

    入力:
      - session_id, provider, model（永続化メタデータ）
      - system_prompt
      - 過去メッセージ履歴（既存セッションの場合のみ）
      - 当該リクエストの user メッセージ
      - LLM クライアント（Factory で生成済み）
      - ツール定義配列（provider 固有形式）
      - ToolInvocationService（MCP ツールディスパッチャ）
      - user_id（ツール側の認可で使う）

    出力:
      - OrchestrationResult: 新規生成された全メッセージ + メタデータ
    """

    def __init__(self, max_iter: int = _DEFAULT_MAX_ITER) -> None:
        self._max_iter = max_iter

    def run(
        self,
        *,
        session_id: int,
        provider: str,
        model: str,
        system_prompt: str,
        previous_messages: list[ChatMessageEntity],
        user_message: str,
        llm_client: AbstractLlmClient,
        tools: list[dict[str, Any]],
        tool_invocation_service: ToolInvocationService,
        user_id: int | None,
    ) -> OrchestrationResult:
        result = OrchestrationResult(session_id=session_id, provider=provider, model_used=model)

        # ユーザーメッセージを最初に積む（永続化対象）
        user_entity = ChatMessageEntity(
            session_id=session_id,
            role="user",
            content=user_message,
            provider=provider,
            model_used=model,
        )
        result.new_messages.append(user_entity)

        # LLM 呼び出し用の中間メッセージ履歴を構築
        # 履歴 (previous_messages) + 今回の user メッセージ
        conversation: list[dict[str, Any]] = [_entity_to_intermediate(m) for m in previous_messages]
        conversation.append(_entity_to_intermediate(user_entity))

        for iteration in range(self._max_iter):
            result.iterations = iteration + 1
            response = llm_client.chat_with_tools(
                system_prompt=system_prompt,
                messages=conversation,
                tools=tools or None,
            )

            result.total_prompt_tokens += response.prompt_tokens
            result.total_completion_tokens += response.completion_tokens

            # assistant メッセージを永続化対象に追加
            tool_calls_dump = [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
            assistant_entity = ChatMessageEntity(
                session_id=session_id,
                role="assistant",
                content=response.content,
                tool_args={"tool_calls": tool_calls_dump} if tool_calls_dump else {},
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                model_used=response.model,
                provider=provider,
            )
            result.new_messages.append(assistant_entity)

            # ツール呼び出しが無ければ終了
            if not response.has_tool_calls:
                result.final_assistant_content = response.content
                return result

            # 次回 LLM 呼び出しのために assistant entry を中間履歴に追加
            conversation.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls,
                }
            )

            # ツール実行 & tool result の積み込み
            for tool_call in response.tool_calls:
                tool_result_dict, error_msg = _safely_invoke_tool(
                    tool_invocation_service=tool_invocation_service,
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    user_id=user_id,
                )
                # 永続化対象に tool メッセージを追加
                tool_entity = ChatMessageEntity(
                    session_id=session_id,
                    role="tool",
                    content=error_msg or json.dumps(tool_result_dict, ensure_ascii=False),
                    tool_name=tool_call.name,
                    tool_args=dict(tool_call.arguments),
                    tool_result=tool_result_dict,
                    provider=provider,
                    model_used=model,
                )
                result.new_messages.append(tool_entity)

                # 次回 LLM 呼び出しのために tool entry を中間履歴に追加
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "content": error_msg or json.dumps(tool_result_dict, ensure_ascii=False),
                    }
                )

        # MAX_ITER に到達して打ち切り
        result.truncated = True
        logger.warning(
            "Function Calling ループが MAX_ITER=%d に到達しました（session_id=%d）",
            self._max_iter,
            session_id,
        )
        # 最終応答が無いケースでは打ち切りメッセージを補う
        if not result.final_assistant_content:
            result.final_assistant_content = (
                "ツール呼び出しが多すぎるため処理を打ち切りました。質問を分割してお試しください。"
            )
        return result


def _entity_to_intermediate(entity: ChatMessageEntity) -> dict[str, Any]:
    """ChatMessageEntity を LLM クライアント中間形式に変換する。"""
    if entity.role == "user":
        return {"role": "user", "content": entity.content}

    if entity.role == "assistant":
        # 過去 assistant メッセージは text のみ送信（過去の tool_calls は対応する
        # tool 応答とセットで保存されており、ループ再開には不要）
        return {"role": "assistant", "content": entity.content}

    if entity.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": "",  # 過去履歴では正確な call_id は不要
            "tool_name": entity.tool_name or "",
            "content": json.dumps(entity.tool_result, ensure_ascii=False) if entity.tool_result else entity.content,
        }

    return {"role": entity.role, "content": entity.content}


def _safely_invoke_tool(
    *,
    tool_invocation_service: ToolInvocationService,
    tool_name: str,
    arguments: dict[str, Any],
    user_id: int | None,
) -> tuple[dict[str, Any], str | None]:
    """ツール呼び出し。例外は捕捉してエラーメッセージを返す（ループは継続）。

    Returns:
        (result_dict, error_message): エラー時は result_dict={}, error_message=str
    """
    try:
        result = tool_invocation_service.invoke(
            tool_name=tool_name,
            params=arguments,
            user_id=user_id,
        )
        return result, None
    except PermissionError as exc:
        # 未認証ユーザーが USER_REQUIRED_TOOLS を呼んだ場合
        return {}, f"ツール '{tool_name}' の実行には認証が必要です: {exc}"
    except ChatToolInvocationError:
        raise
    except Exception as exc:  # noqa: BLE001 - ループ継続のため広く捕捉
        logger.exception("ツール実行失敗: %s", tool_name)
        return {}, f"ツール '{tool_name}' の実行中にエラーが発生しました: {exc}"
