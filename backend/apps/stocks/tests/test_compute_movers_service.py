"""compute_movers_service 純関数のテスト（DB 不要）。"""

from __future__ import annotations

import datetime
from decimal import Decimal

from apps.stocks.application.services.compute_movers_service import (
    MoversInput,
    compute_one,
)
from apps.stocks.domain.entities import PriceEntity


def _price(
    *,
    date_str: str,
    close: str,
    volume: int | None = 100000,
    is_limit_up: bool = False,
    is_limit_down: bool = False,
) -> PriceEntity:
    return PriceEntity(
        stock_id=1,
        date=date_str,
        close_price=Decimal(close),
        volume=volume,
        is_limit_up=is_limit_up,
        is_limit_down=is_limit_down,
    )


class TestComputeOne:
    def test_calculates_change_pct_and_volume_ratio(self) -> None:
        prices = [_price(date_str="2026-05-15", close="2850", volume=380000)]
        for i in range(20):
            prices.append(_price(date_str=f"2026-04-{i + 1:02d}", close="2350", volume=100000))

        result = compute_one(MoversInput(stock_id=1, prices_desc=prices))

        assert result is not None
        assert result.date == datetime.date(2026, 5, 15)
        assert result.close_price == Decimal("2850")
        assert result.prev_close == Decimal("2350")
        assert result.change_pct == Decimal("21.2766")
        assert result.volume_ratio_20d == Decimal("3.80")

    def test_returns_none_when_empty(self) -> None:
        assert compute_one(MoversInput(stock_id=1, prices_desc=[])) is None

    def test_returns_none_when_target_date_not_found(self) -> None:
        prices = [_price(date_str="2026-05-15", close="100")]
        result = compute_one(
            MoversInput(stock_id=1, prices_desc=prices),
            target_date=datetime.date(2026, 5, 14),
        )
        assert result is None

    def test_change_pct_null_when_no_prev_close(self) -> None:
        prices = [_price(date_str="2026-05-15", close="100")]
        result = compute_one(MoversInput(stock_id=1, prices_desc=prices))
        assert result is not None
        assert result.change_pct is None
        assert result.prev_close is None

    def test_volume_ratio_null_when_insufficient_history(self) -> None:
        prices = [
            _price(date_str="2026-05-15", close="100", volume=100000),
            _price(date_str="2026-05-14", close="100", volume=100000),
        ]
        result = compute_one(MoversInput(stock_id=1, prices_desc=prices))
        assert result is not None
        assert result.volume_ratio_20d is None

    def test_volume_ratio_null_when_today_volume_zero(self) -> None:
        prices = [_price(date_str="2026-05-15", close="100", volume=0)]
        for i in range(20):
            prices.append(_price(date_str=f"2026-04-{i + 1:02d}", close="100", volume=100000))
        result = compute_one(MoversInput(stock_id=1, prices_desc=prices))
        assert result is not None
        assert result.volume_ratio_20d is None

    def test_propagates_limit_flags(self) -> None:
        prices = [
            _price(date_str="2026-05-15", close="2850", is_limit_up=True),
            _price(date_str="2026-05-14", close="2350"),
        ]
        result = compute_one(MoversInput(stock_id=1, prices_desc=prices))
        assert result is not None
        assert result.is_limit_up is True
        assert result.is_limit_down is False
