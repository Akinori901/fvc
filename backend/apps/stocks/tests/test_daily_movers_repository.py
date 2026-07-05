"""DailyMoversRepository の DB テスト。"""

from __future__ import annotations

import datetime
import os
from decimal import Decimal

import pytest

from apps.stocks.domain.entities import DailyMoversEntity
from apps.stocks.infrastructure.repositories import DjangoDailyMoversRepository
from apps.stocks.models import DailyMovers, Stock

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS") == "1",
    reason="DB アクセスが必要なテストはスキップ（SKIP_DB_TESTS=1）",
)


def _make_entity(stock_id: int, target_date: datetime.date, change_pct: Decimal = Decimal("10.0")) -> DailyMoversEntity:
    return DailyMoversEntity(
        stock_id=stock_id,
        date=target_date,
        close_price=Decimal("1000"),
        prev_close=Decimal("900"),
        change_pct=change_pct,
        volume=100000,
        volume_ratio_20d=Decimal("2.0"),
        is_limit_up=False,
        is_limit_down=False,
    )


@pytest.mark.django_db
class TestDjangoDailyMoversRepository:
    def setup_method(self) -> None:
        self.repo = DjangoDailyMoversRepository()

    def test_bulk_replace_inserts_and_replaces(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        sony = Stock.objects.create(code="6758", name="ソニーG")
        target = datetime.date(2026, 5, 15)

        # 初回挿入
        count = self.repo.bulk_replace(
            target,
            [_make_entity(toyota.pk, target, Decimal("21.28")), _make_entity(sony.pk, target, Decimal("-15.0"))],
        )
        assert count == 2
        assert DailyMovers.objects.filter(date=target).count() == 2

        # 再実行で完全置換
        count = self.repo.bulk_replace(target, [_make_entity(toyota.pk, target, Decimal("5.0"))])
        assert count == 1
        assert DailyMovers.objects.filter(date=target).count() == 1

    def test_find_latest_date(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        self.repo.bulk_replace(datetime.date(2026, 5, 14), [_make_entity(toyota.pk, datetime.date(2026, 5, 14))])
        self.repo.bulk_replace(datetime.date(2026, 5, 15), [_make_entity(toyota.pk, datetime.date(2026, 5, 15))])
        assert self.repo.find_latest_date() == datetime.date(2026, 5, 15)

    def test_find_latest_date_empty(self) -> None:
        assert self.repo.find_latest_date() is None

    def test_find_by_date_and_stock_ids(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        sony = Stock.objects.create(code="6758", name="ソニーG")
        target = datetime.date(2026, 5, 15)
        self.repo.bulk_replace(
            target,
            [_make_entity(toyota.pk, target), _make_entity(sony.pk, target)],
        )

        results = self.repo.find_by_date_and_stock_ids(target, [toyota.pk])
        assert len(results) == 1
        assert results[0].stock_id == toyota.pk

    def test_find_by_date_and_stock_ids_empty_list(self) -> None:
        results = self.repo.find_by_date_and_stock_ids(datetime.date(2026, 5, 15), [])
        assert results == []
