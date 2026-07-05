"""チャット機能のリポジトリ ABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from apps.chat.domain.entities import ChatMessageEntity, ChatSessionEntity


class ChatSessionRepository(ABC):
    """チャットセッションの永続化境界。"""

    @abstractmethod
    def find_by_id(self, session_id: int) -> ChatSessionEntity | None:
        """セッション ID から取得（所有者チェックは UseCase 側で行う）。"""

    @abstractmethod
    def list_by_user_id(self, user_id: int, limit: int = 50) -> list[ChatSessionEntity]:
        """ユーザーのセッション一覧を `last_message_at` 降順で返す。"""

    @abstractmethod
    def save(self, session: ChatSessionEntity) -> ChatSessionEntity:
        """新規作成 or 更新。`id` が None なら INSERT、それ以外は UPDATE。

        保存後の最新状態（id / started_at / last_message_at 付き）を返す。
        """

    @abstractmethod
    def touch(self, session_id: int) -> None:
        """`last_message_at` を現在時刻で更新する。"""

    @abstractmethod
    def delete(self, session_id: int) -> None:
        """セッションを削除（関連メッセージも CASCADE で消える）。"""


class ChatMessageRepository(ABC):
    """チャットメッセージの永続化境界。"""

    @abstractmethod
    def list_by_session_id(self, session_id: int, limit: int | None = None) -> list[ChatMessageEntity]:
        """セッション内メッセージを `created_at` 昇順で返す。

        `limit` 指定時は最新 N 件のみ（履歴コンテキスト構築用）。
        """

    @abstractmethod
    def save(self, message: ChatMessageEntity) -> ChatMessageEntity:
        """メッセージを保存して最新状態を返す。"""

    @abstractmethod
    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        """指定ユーザーの `role='user'` メッセージ数を `since` 以降で集計する。

        日次安全弁（DailyLimitService）から呼ばれる。
        """
