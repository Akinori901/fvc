"""PR5 で追加した get_my_dividends_calendar UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from apps.mcp.application.usecases.tools.get_my_dividends_calendar_usecase import (
    GetMyDividendsCalendarToolUseCase,
)


def _holding(*, stock_id: int | None = 100, quantity: Decimal | None = Decimal("100")) -> MagicMock:
    h = MagicMock()
    h.stock_id = stock_id
    h.quantity = quantity
    return h


def _snapshot(*, account_id: int = 1, holdings: list[MagicMock] | None = None) -> MagicMock:
    s = MagicMock()
    s.account_id = account_id
    s.holdings = holdings or []
    return s


def _dividend(
    *,
    stock_id: int = 100,
    ex_date: datetime.date = datetime.date(2026, 6, 28),
    dps: Decimal = Decimal("30.0"),
    record_date: datetime.date | None = None,
    payable_date: datetime.date | None = None,
) -> MagicMock:
    d = MagicMock()
    d.stock_id = stock_id
    d.ex_dividend_date = ex_date
    d.dividends_per_share = dps
    d.record_date = record_date
    d.payable_date = payable_date
    d.source = "yfinance"
    return d


def _stock(id_: int, code: str, name: str) -> MagicMock:
    s = MagicMock()
    s.id = id_
    s.code = code
    s.name = name
    return s


class TestGetMyDividendsCalendarToolUseCase:
    def setup_method(self) -> None:
        self.snapshot_repo = MagicMock()
        self.stock_repo = MagicMock()
        self.dividend_repo = MagicMock()
        self.usecase = GetMyDividendsCalendarToolUseCase(
            snapshot_repo=self.snapshot_repo,
            stock_repo=self.stock_repo,
            dividend_repo=self.dividend_repo,
        )

    def test_returns_dividends_with_expected_amount(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = [
            _snapshot(holdings=[_holding(stock_id=100, quantity=Decimal("100"))])
        ]
        self.dividend_repo.find_upcoming_by_stock_ids.return_value = [
            _dividend(stock_id=100, dps=Decimal("30.0"), payable_date=datetime.date(2026, 8, 31))
        ]
        self.stock_repo.find_by_id.return_value = _stock(100, "8316", "三井住友FG")

        result = self.usecase.execute(user_id=2)
        assert result["months_ahead"] == 3
        assert len(result["upcoming"]) == 1
        item = result["upcoming"][0]
        assert item["code"] == "8316"
        assert item["dividend_per_share"] == "30.0"
        assert item["quantity"] == "100"
        assert item["expected_amount"] == "3000"  # 30 * 100
        assert item["payable_date"] == "2026-08-31"
        assert result["total_expected_amount"] == "3000"
        assert result["warnings"] == []

    def test_aggregates_quantity_across_accounts(self) -> None:
        # 同じ stock_id を 2 つの口座で保有 → 合算
        self.snapshot_repo.find_latest_by_user.return_value = [
            _snapshot(account_id=1, holdings=[_holding(stock_id=100, quantity=Decimal("100"))]),
            _snapshot(account_id=2, holdings=[_holding(stock_id=100, quantity=Decimal("200"))]),
        ]
        self.dividend_repo.find_upcoming_by_stock_ids.return_value = [_dividend(stock_id=100, dps=Decimal("30"))]
        self.stock_repo.find_by_id.return_value = _stock(100, "8316", "三井住友FG")

        result = self.usecase.execute(user_id=2)
        item = result["upcoming"][0]
        assert item["quantity"] == "300"
        assert item["expected_amount"] == "9000"  # 30 * 300

    def test_returns_empty_when_no_holdings(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = []
        result = self.usecase.execute(user_id=2)
        assert result["upcoming"] == []
        assert result["total_expected_amount"] == "0"
        self.dividend_repo.find_upcoming_by_stock_ids.assert_not_called()

    def test_warns_when_holdings_but_no_dividends(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = [_snapshot(holdings=[_holding(stock_id=100)])]
        self.dividend_repo.find_upcoming_by_stock_ids.return_value = []
        result = self.usecase.execute(user_id=2)
        assert result["upcoming"] == []
        assert "data_may_be_incomplete" in result["warnings"]

    def test_respects_months_ahead(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = [_snapshot(holdings=[_holding(stock_id=100)])]
        self.dividend_repo.find_upcoming_by_stock_ids.return_value = []

        self.usecase.execute(user_id=2, months_ahead=6)
        call_args = self.dividend_repo.find_upcoming_by_stock_ids.call_args
        from_date = call_args.kwargs["from_date"]
        to_date = call_args.kwargs["to_date"]
        days_diff = (to_date - from_date).days
        assert days_diff >= 180  # 6 ヶ月 ≈ 180 日

    def test_skips_holdings_without_stock_id_or_zero_quantity(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = [
            _snapshot(
                holdings=[
                    _holding(stock_id=None),
                    _holding(stock_id=100, quantity=Decimal("0")),
                    _holding(stock_id=200, quantity=Decimal("50")),
                ]
            )
        ]
        self.dividend_repo.find_upcoming_by_stock_ids.return_value = []
        self.usecase.execute(user_id=2)
        # stock_ids には 200 のみが渡される
        call_args = self.dividend_repo.find_upcoming_by_stock_ids.call_args
        assert call_args.args[0] == [200]
