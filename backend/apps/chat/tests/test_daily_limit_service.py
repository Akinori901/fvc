"""DailyLimitService のテスト。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from apps.chat.application.services.daily_limit_service import DailyLimitService
from apps.chat.domain.exceptions import ChatDailyLimitExceededError

if TYPE_CHECKING:
    from apps.chat.domain.entities import ChatMessageEntity


_JST = timezone(timedelta(hours=9), name="JST")


class _FakeMessageRepo:
    """count_by_user_since の戻り値だけ制御するモック。"""

    def __init__(self, counts: dict[tuple[int, datetime], int]) -> None:
        """counts: {(user_id, since_utc): count} の事前登録。"""
        self.counts = counts
        self.calls: list[tuple[int, datetime]] = []

    def list_by_session_id(
        self,
        session_id: int,
        limit: int | None = None,
    ) -> list[ChatMessageEntity]:
        return []

    def save(self, message: ChatMessageEntity) -> ChatMessageEntity:
        return message

    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        self.calls.append((user_id, since))
        # tz-naive と tz-aware の比較を避けるため、since を完全一致で探す。
        # テストでは事前に正確な値を登録する。
        return self.counts.get((user_id, since), 0)


def _jst_midnight_utc_for(date_str: str) -> datetime:
    """'2026-05-21' を渡すと、その日の JST 0:00 を UTC に直して返す。"""
    y, m, d = (int(x) for x in date_str.split("-"))
    midnight_jst = datetime(y, m, d, 0, 0, tzinfo=_JST)
    return midnight_jst.astimezone(UTC)


class TestDailyLimitServiceCheck:
    def test_under_limit_returns_current(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 100})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        current = service.check_and_raise(user_id=42, now=now)
        assert current == 100

    def test_at_limit_raises(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 200})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        with pytest.raises(ChatDailyLimitExceededError) as exc_info:
            service.check_and_raise(user_id=42, now=now)
        assert exc_info.value.limit == 200
        assert exc_info.value.current == 200

    def test_over_limit_raises(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 250})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]
        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        with pytest.raises(ChatDailyLimitExceededError):
            service.check_and_raise(user_id=42, now=now)

    def test_users_are_independent(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 200, (43, since): 0})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]
        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        # user_id=43 は別ユーザーなのでブロックされない
        assert service.check_and_raise(user_id=43, now=now) == 0


class TestDailyLimitServiceJstBoundary:
    def test_pre_jst_midnight_uses_previous_day_midnight(self) -> None:
        """JST 23:59:59 → 'since' は当日 0:00 JST"""
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 199})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 21, 23, 59, tzinfo=_JST).astimezone(UTC)
        assert service.check_and_raise(user_id=42, now=now) == 199

    def test_post_jst_midnight_resets(self) -> None:
        """JST 00:00:01 → 'since' は当日 0:00 JST = カウントゼロから始まる"""
        new_since = _jst_midnight_utc_for("2026-05-22")
        old_since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, old_since): 200, (42, new_since): 0})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 22, 0, 0, 1, tzinfo=_JST).astimezone(UTC)
        # 翌日 0:00 直後 → カウントは 0 でブロックされない
        assert service.check_and_raise(user_id=42, now=now) == 0


class TestDailyLimitServiceRemaining:
    def test_remaining_subtracts_current(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 50})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        assert service.remaining(user_id=42, now=now) == 150

    def test_remaining_never_negative(self) -> None:
        since = _jst_midnight_utc_for("2026-05-21")
        repo = _FakeMessageRepo({(42, since): 500})
        service = DailyLimitService(repo, limit_per_day=200)  # type: ignore[arg-type]

        now = datetime(2026, 5, 21, 10, 0, tzinfo=_JST).astimezone(UTC)
        assert service.remaining(user_id=42, now=now) == 0
