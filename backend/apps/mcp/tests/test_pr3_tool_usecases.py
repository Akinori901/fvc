"""PR3 で追加した get_price_movers UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.get_price_movers_usecase import (
    GetPriceMoversToolUseCase,
)


def _movers_entry(
    *,
    stock_id: int = 100,
    change_pct: Decimal | None = Decimal("10"),
    volume_ratio: Decimal | None = Decimal("2.5"),
    is_limit_up: bool = False,
    is_limit_down: bool = False,
    close: Decimal = Decimal("1000"),
    prev: Decimal | None = Decimal("900"),
) -> MagicMock:
    e = MagicMock()
    e.stock_id = stock_id
    e.change_pct = change_pct
    e.volume_ratio_20d = volume_ratio
    e.is_limit_up = is_limit_up
    e.is_limit_down = is_limit_down
    e.close_price = close
    e.prev_close = prev
    e.volume = 100000
    return e


def _stock(stock_id: int, code: str, name: str) -> MagicMock:
    s = MagicMock()
    s.id = stock_id
    s.code = code
    s.name = name
    return s


class TestGetPriceMoversToolUseCase:
    def setup_method(self) -> None:
        self.movers_repo = MagicMock()
        self.stock_repo = MagicMock()
        self.snapshot_repo = MagicMock()
        self.watchlist_repo = MagicMock()
        self.usecase = GetPriceMoversToolUseCase(
            movers_repo=self.movers_repo,
            stock_repo=self.stock_repo,
            snapshot_repo=self.snapshot_repo,
            watchlist_repo=self.watchlist_repo,
        )

    def test_returns_gainers_and_losers_above_threshold(self) -> None:
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        self.movers_repo.find_by_date.return_value = [
            _movers_entry(stock_id=1, change_pct=Decimal("21.28")),
            _movers_entry(stock_id=2, change_pct=Decimal("3.0")),  # threshold 未満
            _movers_entry(stock_id=3, change_pct=Decimal("-15.0")),
        ]
        self.stock_repo.find_by_id.side_effect = lambda sid: _stock(sid, f"S{sid}", f"name{sid}")

        result = self.usecase.execute(threshold_pct=Decimal("5.0"))

        assert result["as_of"] == "2026-05-15"
        assert len(result["gainers"]) == 1
        assert result["gainers"][0]["code"] == "S1"
        assert len(result["losers"]) == 1
        assert result["losers"][0]["code"] == "S3"

    def test_include_limit_hits_overrides_threshold(self) -> None:
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        self.movers_repo.find_by_date.return_value = [
            _movers_entry(stock_id=1, change_pct=Decimal("2.0"), is_limit_up=True),  # threshold 未満だが UL
        ]
        self.stock_repo.find_by_id.side_effect = lambda sid: _stock(sid, "S1", "name")

        result = self.usecase.execute(threshold_pct=Decimal("5.0"), include_limit_hits=True)
        assert len(result["gainers"]) == 1
        assert result["gainers"][0]["is_limit_up"] is True

    def test_min_volume_ratio_filter(self) -> None:
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        self.movers_repo.find_by_date.return_value = [
            _movers_entry(stock_id=1, change_pct=Decimal("10"), volume_ratio=Decimal("3.0")),
            _movers_entry(stock_id=2, change_pct=Decimal("10"), volume_ratio=Decimal("1.0")),
        ]
        self.stock_repo.find_by_id.side_effect = lambda sid: _stock(sid, f"S{sid}", "n")

        result = self.usecase.execute(min_volume_ratio=Decimal("2.0"))
        assert len(result["gainers"]) == 1
        assert result["gainers"][0]["code"] == "S1"

    def test_scope_my_watchlist_uses_watchlist_stock_ids(self) -> None:
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        watch_item = MagicMock()
        watch_item.stock_id = 100
        self.watchlist_repo.find_by_user.return_value = [watch_item]
        self.movers_repo.find_by_date_and_stock_ids.return_value = [_movers_entry(stock_id=100)]
        self.stock_repo.find_by_id.side_effect = lambda sid: _stock(sid, "5892", "yutori")

        result = self.usecase.execute(scope="my_watchlist", user_id=2)
        assert result["scope"] == "my_watchlist"
        self.movers_repo.find_by_date_and_stock_ids.assert_called_once_with(datetime.date(2026, 5, 15), [100])

    def test_scope_my_holdings_requires_user_id(self) -> None:
        with pytest.raises(PermissionError):
            self.usecase.execute(scope="my_holdings", user_id=None)

    def test_invalid_direction_raises(self) -> None:
        with pytest.raises(ValueError):
            self.usecase.execute(direction="invalid")

    def test_returns_empty_when_no_data(self) -> None:
        self.movers_repo.find_latest_date.return_value = None
        result = self.usecase.execute()
        assert result["as_of"] is None
        assert result["gainers"] == []
        assert result["losers"] == []

    def test_limit_applies_to_each_direction(self) -> None:
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        self.movers_repo.find_by_date.return_value = [
            _movers_entry(stock_id=i, change_pct=Decimal(str(10 + i))) for i in range(5)
        ]
        self.stock_repo.find_by_id.side_effect = lambda sid: _stock(sid, f"S{sid}", "n")

        result = self.usecase.execute(limit=2)
        assert len(result["gainers"]) == 2
        # 上位 2 件は change_pct が大きい順
        assert result["gainers"][0]["code"] == "S4"
        assert result["gainers"][1]["code"] == "S3"
