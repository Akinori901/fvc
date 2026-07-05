"""SendChatMessageUseCase のテスト。

依存（AiConfigRepo / ChatSession/MessageRepo / DailyLimit /
ChatOrchestration / LlmClientFactory / ToolDefinition / ToolInvocation）を
すべてフェイクに置き換え、UseCase の判断ロジックを検証する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest

from apps.ai.domain.entities import AiConfigEntity
from apps.chat.application.dto import SendMessageRequestDTO
from apps.chat.application.services.chat_orchestration_service import (
    OrchestrationResult,
)
from apps.chat.application.usecases.send_chat_message_usecase import (
    SendChatMessageUseCase,
)
from apps.chat.domain.entities import ChatMessageEntity, ChatSessionEntity
from apps.chat.domain.exceptions import (
    ChatConfigMissingError,
    ChatDailyLimitExceededError,
    ChatSessionNotFoundError,
)

if TYPE_CHECKING:
    from datetime import datetime


@pytest.fixture(autouse=True)
def _disable_transaction_atomic() -> Any:
    """テスト用に execute 内の `with transaction.atomic():` を no-op に差し替える。

    本テストは依存をフェイクに置換しており DB を使わない。
    """
    from contextlib import contextmanager

    @contextmanager
    def _noop_cm() -> Any:
        yield

    with patch(
        "apps.chat.application.usecases.send_chat_message_usecase.transaction.atomic",
        side_effect=_noop_cm,
    ):
        yield


# ────────────────────────────────────────────────────────────────
# フェイク実装
# ────────────────────────────────────────────────────────────────


class _FakeAiConfigRepo:
    def __init__(self, config: AiConfigEntity | None = None) -> None:
        self.config = config

    def find_by_user_id(self, user_id: int) -> AiConfigEntity | None:
        return self.config

    def save(self, entity: AiConfigEntity) -> AiConfigEntity:
        return entity


class _FakeChatSessionRepo:
    def __init__(self, existing: dict[int, ChatSessionEntity] | None = None) -> None:
        self.sessions = existing or {}
        self.next_id = 100
        self.touched: list[int] = []

    def find_by_id(self, session_id: int) -> ChatSessionEntity | None:
        return self.sessions.get(session_id)

    def list_by_user_id(self, user_id: int, limit: int = 50) -> list[ChatSessionEntity]:
        return [s for s in self.sessions.values() if s.user_id == user_id][:limit]

    def save(self, session: ChatSessionEntity) -> ChatSessionEntity:
        if session.id is None:
            session.id = self.next_id
            self.next_id += 1
        self.sessions[session.id] = session
        return session

    def touch(self, session_id: int) -> None:
        self.touched.append(session_id)

    def delete(self, session_id: int) -> None:
        self.sessions.pop(session_id, None)


class _FakeMessageRepo:
    def __init__(self, daily_count: int = 0) -> None:
        self.saved: list[ChatMessageEntity] = []
        self.daily_count = daily_count

    def list_by_session_id(self, session_id: int, limit: int | None = None) -> list[ChatMessageEntity]:
        return []

    def save(self, message: ChatMessageEntity) -> ChatMessageEntity:
        self.saved.append(message)
        return message

    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        return self.daily_count


class _FakeDailyLimitService:
    def __init__(self, allow: bool = True) -> None:
        self.allow = allow
        self.calls: list[int] = []

    def check_and_raise(self, user_id: int, *, now: datetime | None = None) -> int:
        self.calls.append(user_id)
        if not self.allow:
            raise ChatDailyLimitExceededError(limit=200, current=200)
        return 50

    def remaining(self, user_id: int, *, now: datetime | None = None) -> int:
        return 150

    @property
    def limit(self) -> int:
        return 200


class _FakeLlmClientFactory:
    def create(self, provider: str, api_key: str, model: str) -> object:
        return object()


class _FakeToolDefinitionService:
    def build_tools_for_provider(self, provider: str, user_id: int | None) -> list[dict[str, Any]]:
        return []

    def list_phase1_tool_names(self) -> tuple[str, ...]:
        return ()


class _FakeChatOrchestrationService:
    """run() の入出力を記録する。"""

    def __init__(
        self,
        *,
        final_content: str = "応答",
        tool_messages: list[tuple[str, dict[str, Any], bool]] | None = None,
        truncated: bool = False,
    ) -> None:
        self.final_content = final_content
        self.tool_messages = tool_messages or []
        self.truncated = truncated
        self.run_calls: list[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> OrchestrationResult:
        self.run_calls.append(kwargs)
        session_id = kwargs["session_id"]
        new_messages: list[ChatMessageEntity] = [
            ChatMessageEntity(session_id=session_id, role="user", content=kwargs["user_message"]),
        ]
        for tool_name, tool_args, succeeded in self.tool_messages:
            new_messages.append(
                ChatMessageEntity(
                    session_id=session_id,
                    role="tool",
                    tool_name=tool_name,
                    tool_args=dict(tool_args),
                    tool_result={"ok": True} if succeeded else {},
                    content="result" if succeeded else "error",
                )
            )
        new_messages.append(ChatMessageEntity(session_id=session_id, role="assistant", content=self.final_content))
        return OrchestrationResult(
            session_id=session_id,
            new_messages=new_messages,
            final_assistant_content=self.final_content,
            total_prompt_tokens=100,
            total_completion_tokens=50,
            iterations=1,
            truncated=self.truncated,
            model_used=kwargs["model"],
            provider=kwargs["provider"],
        )


class _FakeToolInvocationService:
    def invoke(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        return {}


# ────────────────────────────────────────────────────────────────
# フィクスチャ
# ────────────────────────────────────────────────────────────────


def _make_byok_config(provider: str = "gemini", model: str = "gemini-2.5-flash") -> AiConfigEntity:
    return AiConfigEntity(
        user_id=42,
        provider=provider,
        api_key="user-key",
        model=model,
        is_enabled=True,
    )


def _build_usecase(
    *,
    config: AiConfigEntity | None = None,
    allow_limit: bool = True,
    existing_sessions: dict[int, ChatSessionEntity] | None = None,
    orchestration: _FakeChatOrchestrationService | None = None,
) -> tuple[SendChatMessageUseCase, dict[str, Any]]:
    """UseCase + 内部のフェイク群を辞書で返す。テスト側で挙動確認に使う。"""
    fakes: dict[str, Any] = {
        "ai_config": _FakeAiConfigRepo(config=config),
        "session": _FakeChatSessionRepo(existing=existing_sessions),
        "message": _FakeMessageRepo(),
        "daily_limit": _FakeDailyLimitService(allow=allow_limit),
        "llm_factory": _FakeLlmClientFactory(),
        "tool_def": _FakeToolDefinitionService(),
        "orchestration": orchestration or _FakeChatOrchestrationService(),
        "tool_invocation": _FakeToolInvocationService(),
    }
    usecase = SendChatMessageUseCase(
        ai_config_repo=fakes["ai_config"],
        session_repo=fakes["session"],
        message_repo=fakes["message"],
        daily_limit_service=fakes["daily_limit"],
        llm_client_factory=fakes["llm_factory"],
        tool_definition_service=fakes["tool_def"],
        chat_orchestration_service=fakes["orchestration"],
        tool_invocation_service=fakes["tool_invocation"],
    )
    return usecase, fakes


# ────────────────────────────────────────────────────────────────
# テスト
# ────────────────────────────────────────────────────────────────


class TestSendChatMessageUseCaseConfigChecks:
    def test_no_config_raises(self) -> None:
        usecase, _ = _build_usecase(config=None)
        with pytest.raises(ChatConfigMissingError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))

    def test_disabled_config_raises(self) -> None:
        cfg = _make_byok_config()
        cfg.is_enabled = False
        usecase, _ = _build_usecase(config=cfg)
        with pytest.raises(ChatConfigMissingError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))

    def test_empty_api_key_raises(self) -> None:
        cfg = _make_byok_config()
        cfg.api_key = ""
        usecase, _ = _build_usecase(config=cfg)
        with pytest.raises(ChatConfigMissingError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))

    def test_unknown_provider_raises(self) -> None:
        cfg = _make_byok_config()
        cfg.provider = "anthropic"
        usecase, _ = _build_usecase(config=cfg)
        with pytest.raises(ChatConfigMissingError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))


class TestSendChatMessageUseCaseDailyLimit:
    def test_daily_limit_blocks(self) -> None:
        usecase, _ = _build_usecase(config=_make_byok_config(), allow_limit=False)
        with pytest.raises(ChatDailyLimitExceededError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))


class TestSendChatMessageUseCaseSession:
    def test_new_session_uses_user_provider(self) -> None:
        cfg = _make_byok_config(provider="gemini", model="gemini-2.5-flash")
        usecase, fakes = _build_usecase(config=cfg)
        result = usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi"))
        # 新規セッションが作成され、provider=gemini が紐づく
        assert result.session_id == 100
        assert fakes["session"].sessions[100].provider == "gemini"
        # touch が呼ばれた
        assert fakes["session"].touched == [100]

    def test_existing_session_owned_by_user(self) -> None:
        cfg = _make_byok_config()
        existing = ChatSessionEntity(id=200, user_id=42, provider="openai")
        usecase, fakes = _build_usecase(
            config=cfg,
            existing_sessions={200: existing},
        )
        result = usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi", session_id=200))
        assert result.session_id == 200
        # 新規セッションは作られない（次の id は 100 のまま）
        assert 100 not in fakes["session"].sessions

    def test_other_users_session_raises(self) -> None:
        cfg = _make_byok_config()
        existing = ChatSessionEntity(id=200, user_id=99, provider="openai")
        usecase, _ = _build_usecase(
            config=cfg,
            existing_sessions={200: existing},
        )
        with pytest.raises(ChatSessionNotFoundError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi", session_id=200))

    def test_nonexistent_session_raises(self) -> None:
        cfg = _make_byok_config()
        usecase, _ = _build_usecase(config=cfg)
        with pytest.raises(ChatSessionNotFoundError):
            usecase.execute(SendMessageRequestDTO(user_id=42, user_message="hi", session_id=99999))


class TestSendChatMessageUseCasePersistence:
    def test_all_messages_persisted(self) -> None:
        cfg = _make_byok_config()
        orchestration = _FakeChatOrchestrationService(
            final_content="3件あります",
            tool_messages=[("get_stock_summary", {"code": "7203"}, True)],
        )
        usecase, fakes = _build_usecase(config=cfg, orchestration=orchestration)
        usecase.execute(SendMessageRequestDTO(user_id=42, user_message="7203は？"))

        # user + tool + assistant の 3 件が保存される
        roles = [m.role for m in fakes["message"].saved]
        assert roles == ["user", "tool", "assistant"]


class TestSendChatMessageUseCaseAdminKey:
    def test_non_superuser_cannot_use_admin_key(self) -> None:
        """is_superuser=False では use_admin_key が無視され、BYOK が使われる。"""
        cfg = _make_byok_config(provider="openai", model="gpt-4o-mini")
        usecase, fakes = _build_usecase(config=cfg)
        usecase.execute(
            SendMessageRequestDTO(user_id=42, user_message="hi", use_admin_key=True),
            is_superuser=False,
        )
        # BYOK が使われたので provider=openai のまま、admin_key 経路は通らない
        assert fakes["orchestration"].run_calls[0]["provider"] == "openai"

    def test_superuser_without_admin_key_falls_back_to_byok(self) -> None:
        """管理者キーが未設定（None）なら BYOK にフォールバック。"""
        cfg = _make_byok_config(provider="gemini")
        usecase, fakes = _build_usecase(config=cfg)

        # admin_key_loader が None を返すケース（環境変数も SSM も未設定）
        from apps.chat.infrastructure import admin_key_loader

        admin_key_loader.reset_cache_for_tests()

        usecase.execute(
            SendMessageRequestDTO(user_id=42, user_message="hi", use_admin_key=True),
            is_superuser=True,
        )
        # 管理者キー無 → BYOK Gemini で動作
        assert fakes["orchestration"].run_calls[0]["provider"] == "gemini"
