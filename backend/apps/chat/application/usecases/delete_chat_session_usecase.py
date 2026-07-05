"""チャットセッション削除 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.chat.domain.exceptions import ChatSessionNotFoundError

if TYPE_CHECKING:
    from apps.chat.domain.repositories import ChatSessionRepository


class DeleteChatSessionUseCase:
    """セッションを削除する。所有者チェック付き。

    ORM の CASCADE で関連メッセージも消える。
    """

    def __init__(self, session_repo: ChatSessionRepository) -> None:
        self._session_repo = session_repo

    def execute(self, user_id: int, session_id: int) -> None:
        session = self._session_repo.find_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise ChatSessionNotFoundError(f"セッション {session_id} が見つかりません")
        self._session_repo.delete(session_id)
