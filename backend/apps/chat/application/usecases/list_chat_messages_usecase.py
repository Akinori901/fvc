"""セッション内メッセージ一覧取得 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.chat.domain.exceptions import ChatSessionNotFoundError

if TYPE_CHECKING:
    from apps.chat.domain.entities import ChatMessageEntity
    from apps.chat.domain.repositories import (
        ChatMessageRepository,
        ChatSessionRepository,
    )


class ListChatMessagesUseCase:
    """指定セッション内の全メッセージを time 昇順で返す。

    所有者チェック付き。他人のセッションには `ChatSessionNotFoundError` で応答する。
    """

    def __init__(
        self,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
    ) -> None:
        self._session_repo = session_repo
        self._message_repo = message_repo

    def execute(self, user_id: int, session_id: int) -> list[ChatMessageEntity]:
        session = self._session_repo.find_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise ChatSessionNotFoundError(f"セッション {session_id} が見つかりません")
        return self._message_repo.list_by_session_id(session_id=session_id)
