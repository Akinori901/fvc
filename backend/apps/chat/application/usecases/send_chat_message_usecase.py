"""チャットメッセージ送信ユースケース。

フロー:
1. BYOK 設定取得 → 未設定なら ChatConfigMissingError
2. 管理者キーフォールバック判定（use_admin_key=True かつ is_superuser のみ）
3. DailyLimitService で安全弁チェック
4. セッション取得 or 新規作成 (provider 固定)
5. 過去メッセージ取得（直近 N 件）
6. ToolDefinitionService で provider 別ツール定義生成
7. LlmClientFactoryService で LLM クライアント生成
8. ChatOrchestrationService.run() で Function Calling ループ
9. 結果メッセージを永続化 + セッション touch
10. レスポンス DTO 返却

`@transaction.atomic` で 9 を保護する。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction

from apps.chat.application.dto import (
    SendMessageRequestDTO,
    SendMessageResponseDTO,
    ToolCallSummaryDTO,
)
from apps.chat.domain.entities import ChatSessionEntity
from apps.chat.domain.exceptions import (
    ChatConfigMissingError,
    ChatSessionNotFoundError,
)

if TYPE_CHECKING:
    from apps.ai.domain.repositories import AiConfigRepository
    from apps.chat.application.services.chat_orchestration_service import (
        ChatOrchestrationService,
    )
    from apps.chat.application.services.daily_limit_service import DailyLimitService
    from apps.chat.application.services.llm_client_factory_service import (
        LlmClientFactoryService,
    )
    from apps.chat.application.services.tool_definition_service import (
        ToolDefinitionService,
    )
    from apps.chat.domain.repositories import (
        ChatMessageRepository,
        ChatSessionRepository,
    )
    from apps.mcp.application.services.tool_invocation_service import (
        ToolInvocationService,
    )

logger = logging.getLogger(__name__)

_HISTORY_LIMIT = 10  # LLM に渡す過去メッセージ件数の上限
_DEFAULT_OPENAI_ADMIN_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = (
    "あなたは日本株の投資判断アシスタントです。利用可能なツールを駆使し、ユーザーの質問に対して"
    "データに基づいた回答をしてください。\n\n"
    "ルール:\n"
    "- 必ず最新のデータをツールで取得してから回答する。記憶や推測で答えない\n"
    "- 投資判断は必ず根拠を示す（PBR / ROE / Gordon Growth fair_value / momentum_signal 等）\n"
    "- ツールが認証エラーを返した場合は「APIキーを /settings で発行・登録してください」と案内\n"
    "- 「私の保有」「私の損益」など個人データは get_my_* ツールで取得\n"
)


class SendChatMessageUseCase:
    """チャットの 1 ターン (= ユーザー入力 → アシスタント応答) を実行する。"""

    def __init__(
        self,
        ai_config_repo: AiConfigRepository,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
        daily_limit_service: DailyLimitService,
        llm_client_factory: LlmClientFactoryService,
        tool_definition_service: ToolDefinitionService,
        chat_orchestration_service: ChatOrchestrationService,
        tool_invocation_service: ToolInvocationService,
    ) -> None:
        self._ai_config_repo = ai_config_repo
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._daily_limit_service = daily_limit_service
        self._llm_client_factory = llm_client_factory
        self._tool_definition_service = tool_definition_service
        self._chat_orchestration_service = chat_orchestration_service
        self._tool_invocation_service = tool_invocation_service

    def execute(
        self,
        request: SendMessageRequestDTO,
        *,
        is_superuser: bool = False,
    ) -> SendMessageResponseDTO:
        with transaction.atomic():
            return self._execute_inner(request, is_superuser=is_superuser)

    def _execute_inner(
        self,
        request: SendMessageRequestDTO,
        *,
        is_superuser: bool,
    ) -> SendMessageResponseDTO:
        # 1. 使用する provider / api_key / model を解決
        provider, api_key, model = self._resolve_provider_credentials(
            user_id=request.user_id,
            use_admin_key=request.use_admin_key,
            is_superuser=is_superuser,
        )

        # 2. 日次安全弁チェック
        self._daily_limit_service.check_and_raise(user_id=request.user_id)

        # 3. セッション取得 or 作成
        if request.session_id is not None:
            session = self._session_repo.find_by_id(request.session_id)
            if session is None or session.user_id != request.user_id:
                raise ChatSessionNotFoundError(f"セッション {request.session_id} が見つかりません")
        else:
            session = self._session_repo.save(ChatSessionEntity(user_id=request.user_id, provider=provider))

        assert session.id is not None  # save 後は必ず id が付与される

        # 4. 過去メッセージを取得（先頭から時系列順、最新 N 件にトリム）
        previous = self._message_repo.list_by_session_id(session_id=session.id, limit=_HISTORY_LIMIT)

        # 5. ツール定義 + LLM クライアント生成
        tools = self._tool_definition_service.build_tools_for_provider(provider=provider, user_id=request.user_id)
        llm_client = self._llm_client_factory.create(provider=provider, api_key=api_key, model=model)

        # 6. Function Calling ループ実行
        orchestration_result = self._chat_orchestration_service.run(
            session_id=session.id,
            provider=provider,
            model=model,
            system_prompt=_SYSTEM_PROMPT,
            previous_messages=previous,
            user_message=request.user_message,
            llm_client=llm_client,
            tools=tools,
            tool_invocation_service=self._tool_invocation_service,
            user_id=request.user_id,
        )

        # 7. 永続化 (transaction.atomic 内)
        self._persist_results(
            session_id=session.id,
            new_messages=orchestration_result.new_messages,
        )

        # 8. レスポンス組み立て
        tool_calls_summary = self._build_tool_calls_summary(orchestration_result)
        return SendMessageResponseDTO(
            session_id=session.id,
            assistant_message=orchestration_result.final_assistant_content,
            provider=provider,
            model=model,
            prompt_tokens=orchestration_result.total_prompt_tokens,
            completion_tokens=orchestration_result.total_completion_tokens,
            iterations=orchestration_result.iterations,
            truncated=orchestration_result.truncated,
            tool_calls_summary=tool_calls_summary,
        )

    def _resolve_provider_credentials(
        self,
        user_id: int,
        use_admin_key: bool,
        is_superuser: bool,
    ) -> tuple[str, str, str]:
        """provider / api_key / model を解決する。

        - use_admin_key=True かつ is_superuser=True かつ管理者キー存在 → "openai_admin"
        - それ以外 → ユーザーの BYOK 設定（gemini or openai）
        - BYOK が未登録 / 無効 → ChatConfigMissingError

        Returns: (provider, api_key, model)
        """
        if use_admin_key and is_superuser:
            from apps.chat.infrastructure.admin_key_loader import get_admin_openai_api_key

            admin_key = get_admin_openai_api_key()
            if admin_key:
                return ("openai_admin", admin_key, _DEFAULT_OPENAI_ADMIN_MODEL)
            # 管理者キーが設定されていない場合は BYOK にフォールバック
            logger.warning("管理者キーが未設定のため、BYOK にフォールバック（user_id=%d）", user_id)

        config = self._ai_config_repo.find_by_user_id(user_id)
        if config is None or not config.is_enabled or not config.api_key or config.provider not in ("gemini", "openai"):
            raise ChatConfigMissingError()
        return (config.provider, config.api_key, config.model)

    def _persist_results(self, session_id: int, new_messages: list) -> None:  # type: ignore[type-arg]
        """生成されたメッセージを保存 + セッション touch。

        execute() 全体が @transaction.atomic 配下のため、本メソッド単独での
        トランザクション宣言は不要。LLM エラー時は呼び出し元の例外で
        セッション作成も含めて全体ロールバックされる。
        """
        for message in new_messages:
            self._message_repo.save(message)
        self._session_repo.touch(session_id)

    @staticmethod
    def _build_tool_calls_summary(orchestration_result: object) -> list[ToolCallSummaryDTO]:
        """OrchestrationResult.new_messages からツール呼び出し要約を生成。

        role=tool のメッセージから tool_name と succeeded（エラー文言の有無）を抽出。
        """
        # 循環参照回避のため遅延インポート
        from apps.chat.application.services.chat_orchestration_service import (
            OrchestrationResult,
        )

        assert isinstance(orchestration_result, OrchestrationResult)

        summary: list[ToolCallSummaryDTO] = []
        for msg in orchestration_result.new_messages:
            if msg.role != "tool":
                continue
            # tool_result が空 dict ならエラー扱い（_safely_invoke_tool の仕様）
            succeeded = bool(msg.tool_result)
            summary.append(
                ToolCallSummaryDTO(
                    tool_name=msg.tool_name or "",
                    arguments=dict(msg.tool_args),
                    succeeded=succeeded,
                )
            )
        return summary
