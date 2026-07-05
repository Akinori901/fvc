"""チャットセッション一覧取得 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.chat.domain.entities import ChatSessionEntity
    from apps.chat.domain.repositories import ChatSessionRepository


class ListChatSessionsUseCase:
    """ユーザーのチャットセッション一覧を返す（last_message_at 降順）。"""

    def __init__(self, session_repo: ChatSessionRepository) -> None:
        self._session_repo = session_repo

    def execute(self, user_id: int, *, limit: int = 50) -> list[ChatSessionEntity]:
        return self._session_repo.list_by_user_id(user_id=user_id, limit=limit)
