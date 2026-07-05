"""PR4 で追加した 2 ツール UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from apps.mcp.application.usecases.tools.get_my_holdings_alerts_usecase import (
    GetMyHoldingsAlertsToolUseCase,
)
from apps.mcp.application.usecases.tools.get_my_margin_positions_usecase import (
    GetMyMarginPositionsToolUseCase,
)


def _account(
    *,
    id_: int = 1,
    trading_type: str = "margin",
    credit_type: str | None = "system_6m",
    interest_rate: Decimal | None = Decimal("0.0285"),
    nickname: str = "楽天信用",
) -> MagicMock:
    a = MagicMock()
    a.id = id_
    a.trading_type = trading_type
    a.margin_credit_type = credit_type
    a.margin_interest_rate = interest_rate
    a.nickname = nickname
    a.institution = "楽天証券"
    return a


def _holding(
    *,
    stock_id: int = 100,
    ticker_code: str = "5892",
    asset_name: str = "yutori",
    quantity: Decimal = Decimal("100"),
    unit_price: Decimal = Decimal("2350"),
    cost_jpy: Decimal | None = Decimal("235000"),
    built_date: datetime.date | None = datetime.date(2026, 4, 15),
) -> MagicMock:
    h = MagicMock()
    h.stock_id = stock_id
    h.ticker_code = ticker_code
    h.asset_name = asset_name
    h.quantity = quantity
    h.unit_price = unit_price
    h.cost_jpy = cost_jpy
    h.built_date = built_date
    return h


def _snapshot(
    *,
    account_id: int = 1,
    snapshot_date: str = "2026-05-01",
    holdings: list[MagicMock] | None = None,
) -> MagicMock:
    s = MagicMock()
    s.account_id = account_id
    s.snapshot_date = snapshot_date
    s.holdings = holdings or []
    return s


# ============================================================
# GetMyMarginPositionsToolUseCase
# ============================================================


class TestGetMyMarginPositionsToolUseCase:
    def test_returns_margin_positions_with_calculations(self) -> None:
        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [_account()]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [_snapshot(holdings=[_holding()])]
        price_source = MagicMock()
        price_source.fetch_latest_prices.return_value = {100: Decimal("2850")}

        usecase = GetMyMarginPositionsToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            price_source=price_source,
        )
        result = usecase.execute(user_id=2)

        assert result["count"] == 1
        p = result["positions"][0]
        assert p["stock_code"] == "5892"
        assert p["credit_type"] == "system_6m"
        assert p["build_price"] == "2350"
        assert p["current_price"] == "2850"
        assert p["cost_jpy"] == "235000"
        assert p["accrued_interest"] is not None
        assert p["genbiki_cash_required"] is not None
        assert p["unrealized_pnl"] == "50000"  # (2850 - 2350) * 100
        assert p["expiry_date"] == "2026-10-12"

    def test_filters_only_margin_accounts(self) -> None:
        spot_acc = _account(id_=1, trading_type="spot")
        margin_acc = _account(id_=2, trading_type="margin")
        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [spot_acc, margin_acc]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [
            _snapshot(account_id=1, holdings=[_holding(ticker_code="7203")]),
            _snapshot(account_id=2, holdings=[_holding(ticker_code="5892")]),
        ]
        price_source = MagicMock()
        price_source.fetch_latest_prices.return_value = {}

        usecase = GetMyMarginPositionsToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            price_source=price_source,
        )
        result = usecase.execute(user_id=2)
        assert result["count"] == 1
        assert result["positions"][0]["stock_code"] == "5892"

    def test_returns_empty_when_no_margin_accounts(self) -> None:
        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [_account(trading_type="spot")]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = []
        usecase = GetMyMarginPositionsToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            price_source=MagicMock(),
        )
        result = usecase.execute(user_id=2)
        assert result == {"count": 0, "as_of": datetime.date.today().isoformat(), "positions": []}


# ============================================================
# GetMyHoldingsAlertsToolUseCase
# ============================================================


def _watch_item(stock_id: int) -> MagicMock:
    w = MagicMock()
    w.stock_id = stock_id
    return w


def _stock(id_: int, code: str, name: str, latest_price: Decimal | None = Decimal("2850")) -> MagicMock:
    s = MagicMock()
    s.id = id_
    s.code = code
    s.name = name
    s.latest_price = latest_price
    return s


class TestGetMyHoldingsAlertsToolUseCase:
    def setup_method(self) -> None:
        self.snapshot_repo = MagicMock()
        self.account_repo = MagicMock()
        self.watchlist_repo = MagicMock()
        self.stock_repo = MagicMock()
        self.price_repo = MagicMock()
        self.movers_repo = MagicMock()
        self.screening_usecase = MagicMock()
        self.earnings_uc = MagicMock()

        self.usecase = GetMyHoldingsAlertsToolUseCase(
            snapshot_repo=self.snapshot_repo,
            account_repo=self.account_repo,
            watchlist_repo=self.watchlist_repo,
            stock_repo=self.stock_repo,
            price_repo=self.price_repo,
            movers_repo=self.movers_repo,
            screening_usecase=self.screening_usecase,
            earnings_calendar_tool_usecase=self.earnings_uc,
        )

    def _setup_user_with_yutori_watch(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = []
        self.account_repo.find_by_user.return_value = []
        self.watchlist_repo.find_by_user.return_value = [_watch_item(stock_id=100)]
        self.stock_repo.find_by_id.return_value = _stock(100, "5892", "yutori")

    def test_returns_empty_when_no_holdings_or_watchlist(self) -> None:
        self.snapshot_repo.find_latest_by_user.return_value = []
        self.account_repo.find_by_user.return_value = []
        self.watchlist_repo.find_by_user.return_value = []
        result = self.usecase.execute(user_id=2)
        assert result["alerts_count"] == 0

    def test_detects_stop_high_alert(self) -> None:
        self._setup_user_with_yutori_watch()
        mover = MagicMock()
        mover.stock_id = 100
        mover.is_limit_up = True
        mover.is_limit_down = False
        mover.change_pct = Decimal("21.28")
        self.movers_repo.find_latest_date.return_value = datetime.date(2026, 5, 15)
        self.movers_repo.find_by_date_and_stock_ids.return_value = [mover]
        self.screening_usecase.execute.return_value = []
        self.price_repo.find_52w_high_low.return_value = None
        self.earnings_uc.execute.return_value = {"available": False}

        result = self.usecase.execute(user_id=2)
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "stop_high_today" in alert_types

    def test_detects_high_severity_risk_tag(self) -> None:
        self._setup_user_with_yutori_watch()
        self.movers_repo.find_latest_date.return_value = None
        result_mock = MagicMock()
        result_mock.long_balance = 500_000
        result_mock.short_balance = 0
        result_mock.avg_turnover_20d = None
        result_mock.current_pbr = None
        result_mock.fair_pbr = None
        result_mock.fair_value = Decimal("1000")
        result_mock.not_calculable_reason = None
        self.screening_usecase.execute.return_value = [result_mock]
        self.price_repo.find_52w_high_low.return_value = None
        self.earnings_uc.execute.return_value = {"available": False}

        result = self.usecase.execute(user_id=2)
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "risk_tag_high_severity" in alert_types

    def test_filters_by_severity_min(self) -> None:
        self._setup_user_with_yutori_watch()
        self.movers_repo.find_latest_date.return_value = None
        self.screening_usecase.execute.return_value = []
        # 52w 高値に 1% 以内 → medium severity アラート
        self.stock_repo.find_by_id.return_value = _stock(100, "5892", "yutori", Decimal("3000"))
        self.price_repo.find_52w_high_low.return_value = (Decimal("3000"), Decimal("1000"))
        self.earnings_uc.execute.return_value = {"available": False}

        # severity_min=high → medium のアラートは除外される
        result = self.usecase.execute(user_id=2, severity_min="high")
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "near_52w_high_breakout" not in alert_types

    def test_includes_52w_breakout_when_within_2pct(self) -> None:
        self._setup_user_with_yutori_watch()
        self.movers_repo.find_latest_date.return_value = None
        self.screening_usecase.execute.return_value = []
        # 高値 3000、現在 2970 → -1.0% (2% 以内)
        self.stock_repo.find_by_id.return_value = _stock(100, "5892", "yutori", Decimal("2970"))
        self.price_repo.find_52w_high_low.return_value = (Decimal("3000"), Decimal("1000"))
        self.earnings_uc.execute.return_value = {"available": False}

        result = self.usecase.execute(user_id=2)
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "near_52w_high_breakout" in alert_types

    def test_handles_earnings_calendar_failure_gracefully(self) -> None:
        self._setup_user_with_yutori_watch()
        self.movers_repo.find_latest_date.return_value = None
        self.screening_usecase.execute.return_value = []
        self.price_repo.find_52w_high_low.return_value = None
        self.earnings_uc.execute.side_effect = RuntimeError("J-Quants unavailable")

        # 例外で落ちず、空のアラートで返る
        result = self.usecase.execute(user_id=2)
        assert result["alerts_count"] == 0
