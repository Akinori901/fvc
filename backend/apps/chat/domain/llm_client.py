"""LLM クライアントの共通インターフェース。

OpenAI / Gemini など provider 別の実装を、apps/chat の Function Calling ループから
provider 非依存で扱うための抽象。

ツール定義（tools）の形式は provider ごとに異なるため、apps/chat の
ToolDefinitionService で provider に応じて生成する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """LLM が要求したツール呼び出し 1 件分。"""

    id: str  # provider 側が割り当てる呼び出し ID（tool_result の紐付けに使う）
    name: str
    arguments: dict[str, Any]


@dataclass
class LlmResponse:
    """LLM の応答。Function Calling 中間応答と最終応答の両方を表現する。"""

    content: str  # 最終応答テキスト（tool_calls 中間応答時は空文字を許容）
    model: str
    prompt_tokens: int
    completion_tokens: int
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class AbstractLlmClient(ABC):
    """Function Calling 対応 LLM クライアントの共通基底。"""

    @abstractmethod
    def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        """会話履歴 + ツール定義で 1 回 LLM を呼び、応答 or tool_calls を返す。

        Args:
            system_prompt: システムプロンプト
            messages: 過去のメッセージ履歴。形式は provider 共通の中間形式
                      [{"role": "user|assistant|tool", "content": "...",
                        "tool_call_id": "...", "tool_calls": [...]}]
                      各クライアント実装が provider 固有形式に変換する。
            tools: provider 固有形式のツール定義配列。None の場合は通常チャット。

        Returns:
            LlmResponse: content + tool_calls のいずれか（または両方）を持つ。
        """
