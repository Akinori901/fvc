"""ChatSessionEntity / ChatMessageEntity のドメインテスト。"""

from __future__ import annotations

from apps.chat.domain.entities import ChatMessageEntity, ChatSessionEntity


class TestChatSessionEntity:
    def test_creates_with_required_fields(self) -> None:
        session = ChatSessionEntity(user_id=1, provider="gemini")
        assert session.user_id == 1
        assert session.provider == "gemini"
        assert session.title == ""
        assert session.id is None
        assert session.started_at is None
        assert session.last_message_at is None

    def test_accepts_openai_admin_provider(self) -> None:
        session = ChatSessionEntity(user_id=42, provider="openai_admin", title="検証用")
        assert session.provider == "openai_admin"
        assert session.title == "検証用"


class TestChatMessageEntity:
    def test_user_message_defaults(self) -> None:
        msg = ChatMessageEntity(session_id=10, role="user", content="7203 の状況は？")
        assert msg.session_id == 10
        assert msg.role == "user"
        assert msg.content == "7203 の状況は？"
        assert msg.tool_name is None
        assert msg.tool_args == {}
        assert msg.tool_result == {}
        assert msg.prompt_tokens == 0
        assert msg.completion_tokens == 0

    def test_tool_message_with_args_and_result(self) -> None:
        msg = ChatMessageEntity(
            session_id=10,
            role="tool",
            tool_name="get_stock_summary",
            tool_args={"code": "7203"},
            tool_result={"code": "7203", "name": "トヨタ自動車"},
        )
        assert msg.tool_name == "get_stock_summary"
        assert msg.tool_args == {"code": "7203"}
        assert msg.tool_result["name"] == "トヨタ自動車"

    def test_independent_default_dicts(self) -> None:
        """field(default_factory=dict) が共有されないこと（dataclass 既知の落とし穴）。"""
        msg_a = ChatMessageEntity(session_id=1, role="tool")
        msg_b = ChatMessageEntity(session_id=2, role="tool")
        msg_a.tool_args["code"] = "7203"
        assert "code" not in msg_b.tool_args
