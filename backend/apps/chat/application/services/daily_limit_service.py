"""1日あたりのチャット質問数を安全弁として制限するサービス。

BYOK のためコスト負担はユーザー側だが、Function Calling 暴走を運営側で
止めるため、日次の質問数（role=user メッセージ数）に上限を設ける。

JST 0時で日次リセット（DB の datetime 比較で実現）。
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING

from apps.chat.domain.exceptions import ChatDailyLimitExceededError

if TYPE_CHECKING:
    from apps.chat.domain.repositories import ChatMessageRepository

_DEFAULT_DAILY_LIMIT = 200
_JST = timezone(timedelta(hours=9), name="JST")


class DailyLimitService:
    """ユーザーごとの 1 日あたりの user メッセージ数を制限する。"""

    def __init__(
        self,
        message_repo: ChatMessageRepository,
        limit_per_day: int = _DEFAULT_DAILY_LIMIT,
    ) -> None:
        self._message_repo = message_repo
        self._limit = limit_per_day

    def check_and_raise(self, user_id: int, *, now: datetime | None = None) -> int:
        """直近 JST 0時以降の質問数をチェック。

        Returns: 現在の使用回数（チェック後）

        Raises: ChatDailyLimitExceededError if 上限到達
        """
        now_utc = now or datetime.now(tz=UTC)
        since_utc = _today_jst_midnight_utc(now_utc)
        current = self._message_repo.count_by_user_since(user_id=user_id, since=since_utc)
        if current >= self._limit:
            raise ChatDailyLimitExceededError(limit=self._limit, current=current)
        return current

    def remaining(self, user_id: int, *, now: datetime | None = None) -> int:
        """残り質問数を返す（UI 表示用）。負数にはならない。"""
        now_utc = now or datetime.now(tz=UTC)
        since_utc = _today_jst_midnight_utc(now_utc)
        current = self._message_repo.count_by_user_since(user_id=user_id, since=since_utc)
        return max(0, self._limit - current)

    @property
    def limit(self) -> int:
        return self._limit


def _today_jst_midnight_utc(now_utc: datetime) -> datetime:
    """与えられた現在時刻（UTC）から見た「今日の JST 0時」を UTC で返す。"""
    now_jst = now_utc.astimezone(_JST)
    midnight_jst = datetime.combine(now_jst.date(), time(0, 0), tzinfo=_JST)
    return midnight_jst.astimezone(UTC)
