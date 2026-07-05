"""チャット例外のテスト。"""

from __future__ import annotations

import pytest

from apps.chat.domain.exceptions import (
    ChatConfigMissingError,
    ChatDailyLimitExceededError,
    ChatError,
    ChatSessionNotFoundError,
    ChatToolInvocationError,
)


class TestChatExceptionsHierarchy:
    def test_all_inherit_from_chat_error(self) -> None:
        assert issubclass(ChatConfigMissingError, ChatError)
        assert issubclass(ChatDailyLimitExceededError, ChatError)
        assert issubclass(ChatSessionNotFoundError, ChatError)
        assert issubclass(ChatToolInvocationError, ChatError)


class TestChatConfigMissingError:
    def test_default_message_in_japanese(self) -> None:
        exc = ChatConfigMissingError()
        assert "設定" in str(exc)

    def test_custom_message(self) -> None:
        exc = ChatConfigMissingError("カスタムメッセージ")
        assert str(exc) == "カスタムメッセージ"


class TestChatDailyLimitExceededError:
    def test_carries_limit_and_current(self) -> None:
        exc = ChatDailyLimitExceededError(limit=200, current=200)
        assert exc.limit == 200
        assert exc.current == 200
        assert "200" in str(exc)

    def test_raises_correctly(self) -> None:
        with pytest.raises(ChatDailyLimitExceededError) as exc_info:
            raise ChatDailyLimitExceededError(limit=200, current=200)
        assert exc_info.value.limit == 200
