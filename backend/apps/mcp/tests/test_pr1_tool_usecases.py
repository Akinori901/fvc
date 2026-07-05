"""PR1 で追加した 4 ツール UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.get_margin_balance_usecase import (
    GetMarginBalanceToolUseCase,
)
from apps.mcp.application.usecases.tools.get_my_holdings_news_usecase import (
    GetMyHoldingsNewsToolUseCase,
)
from apps.mcp.application.usecases.tools.get_my_pnl_usecase import GetMyPnlToolUseCase
from apps.mcp.application.usecases.tools.get_my_portfolio_summary_usecase import (
    GetMyPortfolioSummaryToolUseCase,
)


def _account(
    id_: int = 1,
    family_member_id: int = 10,
    institution: str = "楽天証券",
    asset_class: str = "jp_stock",
    trading_type: str = "spot",
    nickname: str = "",
) -> MagicMock:
    a = MagicMock()
    a.id = id_
    a.family_member_id = family_member_id
    a.institution = institution
    a.asset_class = asset_class
    a.trading_type = trading_type
    a.nickname = nickname
    return a


def _member(id_: int = 10, name: str = "本人") -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.name = name
    return m


def _holding(
    *,
    stock_id: int | None = 100,
    ticker_code: str = "7203",
    asset_name: str = "トヨタ自動車",
    quantity: Decimal | None = Decimal("100"),
    unit_price: Decimal | None = Decimal("2500"),
    cost_jpy: Decimal | None = Decimal("250000"),
    value_jpy: Decimal = Decimal("280000"),
) -> MagicMock:
    h = MagicMock()
    h.stock_id = stock_id
    h.ticker_code = ticker_code
    h.asset_name = asset_name
    h.quantity = quantity
    h.unit_price = unit_price
    h.cost_jpy = cost_jpy
    h.value_jpy = value_jpy
    h.asset_type = "stock"
    return h


def _snapshot(
    account_id: int = 1,
    holdings: list[MagicMock] | None = None,
    total_cost_jpy: Decimal | None = Decimal("250000"),
) -> MagicMock:
    s = MagicMock()
    s.account_id = account_id
    s.holdings = holdings or []
    s.total_cost_jpy = total_cost_jpy
    return s


# ============================================================
# GetMyPortfolioSummaryToolUseCase
# ============================================================


class TestGetMyPortfolioSummaryToolUseCase:
    def test_aggregates_valuation_and_returns_dto(self) -> None:
        acc = _account(id_=1, family_member_id=10, asset_class="jp_stock", trading_type="margin", nickname="楽天信用")
        snap = _snapshot(account_id=1, total_cost_jpy=Decimal("811831"))
        member = _member(id_=10, name="本人")

        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [acc]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        member_repo = MagicMock()
        member_repo.find_by_user.return_value = [member]

        valuation = MagicMock()
        valuation.total_value = Decimal("613900")
        valuation.stock_total = Decimal("613900")
        valuation.non_stock_value = Decimal("0")
        valuation.by_asset_class = {"jp_stock": Decimal("613900")}
        valuation.by_account = {1: Decimal("613900")}
        valuation.by_member = {10: Decimal("613900")}
        valuation_service = MagicMock()
        valuation_service.evaluate.return_value = valuation

        usecase = GetMyPortfolioSummaryToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            member_repo=member_repo,
            valuation_service=valuation_service,
        )
        result = usecase.execute(user_id=2)

        assert result["total_value"] == "613900"
        assert result["total_cost"] == "811831"
        assert result["unrealized_pnl"] == "-197931"
        assert result["by_asset_class"] == {"jp_stock": "613900"}
        assert len(result["by_account"]) == 1
        assert result["by_account"][0]["account_id"] == 1
        assert result["by_account"][0]["trading_type"] == "margin"
        assert result["by_account"][0]["label"] == "楽天信用"
        assert result["by_account"][0]["pnl"] == "-197931"
        assert result["by_member"][0]["member_name"] == "本人"
        assert result["day_change_pct"] is None

    def test_handles_empty_user_with_no_accounts(self) -> None:
        account_repo = MagicMock()
        account_repo.find_by_user.return_value = []
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = []
        member_repo = MagicMock()
        member_repo.find_by_user.return_value = []
        valuation_service = MagicMock()
        empty_val = MagicMock()
        empty_val.total_value = Decimal("0")
        empty_val.stock_total = Decimal("0")
        empty_val.non_stock_value = Decimal("0")
        empty_val.by_asset_class = {}
        empty_val.by_account = {}
        empty_val.by_member = {}
        valuation_service.evaluate.return_value = empty_val

        usecase = GetMyPortfolioSummaryToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            member_repo=member_repo,
            valuation_service=valuation_service,
        )
        result = usecase.execute(user_id=99)
        assert result["total_value"] == "0"
        assert result["total_cost"] is None
        assert result["unrealized_pnl"] is None
        assert result["by_account"] == []


# ============================================================
# GetMyPnlToolUseCase
# ============================================================


class TestGetMyPnlToolUseCase:
    def test_calculates_pnl_per_holding(self) -> None:
        acc = _account(id_=1, trading_type="spot", nickname="楽天")
        h = _holding(stock_id=100, ticker_code="7203", quantity=Decimal("100"), cost_jpy=Decimal("250000"))
        snap = _snapshot(account_id=1, holdings=[h])

        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [acc]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        stock_repo = MagicMock()
        price_source = MagicMock()
        price_source.fetch_latest_prices.return_value = {100: Decimal("2800")}

        usecase = GetMyPnlToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            stock_repo=stock_repo,
            price_source=price_source,
        )
        result = usecase.execute(user_id=2)

        assert len(result["holdings"]) == 1
        item = result["holdings"][0]
        assert item["stock_code"] == "7203"
        assert item["current_price"] == "2800"
        assert item["market_value"] == "280000"
        assert item["unrealized_pnl"] == "30000"
        assert item["unrealized_pnl_pct"] == "12.00"  # 30000/250000 * 100
        assert item["day_change_pct"] is None

    def test_filters_by_code_when_specified(self) -> None:
        acc = _account()
        h1 = _holding(stock_id=100, ticker_code="7203", asset_name="トヨタ")
        h2 = _holding(stock_id=200, ticker_code="5892", asset_name="yutori")
        snap = _snapshot(account_id=1, holdings=[h1, h2])
        target_stock = MagicMock()
        target_stock.id = 200

        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [acc]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = target_stock
        price_source = MagicMock()
        price_source.fetch_latest_prices.return_value = {200: Decimal("2850")}

        usecase = GetMyPnlToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            stock_repo=stock_repo,
            price_source=price_source,
        )
        result = usecase.execute(user_id=2, code="5892")
        assert len(result["holdings"]) == 1
        assert result["holdings"][0]["stock_code"] == "5892"

    def test_returns_null_pnl_when_no_price_or_cost_available(self) -> None:
        acc = _account()
        h = _holding(stock_id=100, cost_jpy=None)
        snap = _snapshot(account_id=1, holdings=[h])

        account_repo = MagicMock()
        account_repo.find_by_user.return_value = [acc]
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        stock_repo = MagicMock()
        price_source = MagicMock()
        price_source.fetch_latest_prices.return_value = {}

        usecase = GetMyPnlToolUseCase(
            account_repo=account_repo,
            snapshot_repo=snapshot_repo,
            stock_repo=stock_repo,
            price_source=price_source,
        )
        result = usecase.execute(user_id=2)
        item = result["holdings"][0]
        assert item["current_price"] is None
        assert item["market_value"] is None
        assert item["unrealized_pnl"] is None


# ============================================================
# GetMarginBalanceToolUseCase
# ============================================================


def _stock(id_: int = 1, code: str = "7203", name: str = "トヨタ自動車") -> MagicMock:
    s = MagicMock()
    s.id = id_
    s.code = code
    s.name = name
    return s


def _margin_entry(
    *,
    date_str: str = "2026-05-15",
    long_balance: int | None = 430500,
    short_balance: int | None = 0,
    sl_ratio: Decimal | None = None,
) -> MagicMock:
    e = MagicMock()
    e.date = datetime.date.fromisoformat(date_str)
    e.long_balance = long_balance
    e.long_balance_change = 5000
    e.short_balance = short_balance
    e.short_balance_change = 0
    e.sl_ratio = sl_ratio
    return e


class TestGetMarginBalanceToolUseCase:
    def test_returns_latest_and_4w_history(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = _stock(id_=42, code="5892", name="yutori")
        margin_repo = MagicMock()
        latest = _margin_entry(date_str="2026-05-15", long_balance=430500, short_balance=100)
        history = [latest, _margin_entry(date_str="2026-05-08", long_balance=425000)]
        margin_repo.find_latest_by_stock_id.return_value = latest
        margin_repo.find_recent_by_stock_id.return_value = history

        usecase = GetMarginBalanceToolUseCase(stock_repo=stock_repo, margin_repo=margin_repo)
        result = usecase.execute(code="5892")

        assert result["code"] == "5892"
        assert result["as_of"] == "2026-05-15"
        assert result["buy_balance_shares"] == 430500
        assert result["sell_balance_shares"] == 100
        assert result["credit_ratio"] == "4305"  # 430500 / 100
        assert len(result["history_last_4w"]) == 2
        margin_repo.find_recent_by_stock_id.assert_called_once_with(42, limit=4)

    def test_raises_when_stock_not_found(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = None
        usecase = GetMarginBalanceToolUseCase(stock_repo=stock_repo, margin_repo=MagicMock())
        with pytest.raises(ValueError):
            usecase.execute(code="0000")

    def test_credit_ratio_none_when_short_balance_zero(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = _stock()
        margin_repo = MagicMock()
        margin_repo.find_latest_by_stock_id.return_value = _margin_entry(long_balance=430500, short_balance=0)
        margin_repo.find_recent_by_stock_id.return_value = []
        usecase = GetMarginBalanceToolUseCase(stock_repo=stock_repo, margin_repo=margin_repo)
        result = usecase.execute(code="7203")
        assert result["credit_ratio"] is None


# ============================================================
# GetMyHoldingsNewsToolUseCase
# ============================================================


def _article(
    *,
    id_: int = 1,
    title: str = "yutori 通期上方修正",
    importance: Decimal | None = Decimal("0.8"),
) -> MagicMock:
    a = MagicMock()
    a.id = id_
    a.title = title
    a.url = "https://example.com"
    a.summary = "サマリ"
    a.category = "stock"
    a.publisher = "kabutan"
    a.language = "ja"
    a.published_at = datetime.datetime(2026, 5, 14, 16, 0, tzinfo=datetime.UTC)
    a.importance_score = importance
    return a


class TestGetMyHoldingsNewsToolUseCase:
    def test_aggregates_stock_ids_from_holdings_and_watchlist(self) -> None:
        snap = _snapshot(account_id=1, holdings=[_holding(stock_id=100), _holding(stock_id=200)])
        watch_item = MagicMock()
        watch_item.stock_id = 300

        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        watchlist_repo = MagicMock()
        watchlist_repo.find_by_user.return_value = [watch_item]
        article_repo = MagicMock()
        article_repo.list_articles_for_stocks.return_value = ([_article()], 1)

        usecase = GetMyHoldingsNewsToolUseCase(
            snapshot_repo=snapshot_repo,
            watchlist_repo=watchlist_repo,
            article_repo=article_repo,
        )
        result = usecase.execute(user_id=2)

        assert result["count"] == 1
        assert result["total"] == 1
        article_repo.list_articles_for_stocks.assert_called_once_with(
            stock_ids=[100, 200, 300],
            days=7,
            min_importance=None,
            limit=20,
        )

    def test_returns_empty_when_no_holdings_or_watchlist(self) -> None:
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = []
        watchlist_repo = MagicMock()
        watchlist_repo.find_by_user.return_value = []
        article_repo = MagicMock()

        usecase = GetMyHoldingsNewsToolUseCase(
            snapshot_repo=snapshot_repo,
            watchlist_repo=watchlist_repo,
            article_repo=article_repo,
        )
        result = usecase.execute(user_id=2)
        assert result == {"count": 0, "total": 0, "articles": []}
        article_repo.list_articles_for_stocks.assert_not_called()

    def test_ignores_holdings_without_stock_id(self) -> None:
        snap = _snapshot(account_id=1, holdings=[_holding(stock_id=None), _holding(stock_id=200)])
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        watchlist_repo = MagicMock()
        watchlist_repo.find_by_user.return_value = []
        article_repo = MagicMock()
        article_repo.list_articles_for_stocks.return_value = ([], 0)

        usecase = GetMyHoldingsNewsToolUseCase(
            snapshot_repo=snapshot_repo,
            watchlist_repo=watchlist_repo,
            article_repo=article_repo,
        )
        usecase.execute(user_id=2)
        article_repo.list_articles_for_stocks.assert_called_once_with(
            stock_ids=[200],
            days=7,
            min_importance=None,
            limit=20,
        )

    def test_passes_optional_filters(self) -> None:
        snap = _snapshot(account_id=1, holdings=[_holding(stock_id=100)])
        snapshot_repo = MagicMock()
        snapshot_repo.find_latest_by_user.return_value = [snap]
        watchlist_repo = MagicMock()
        watchlist_repo.find_by_user.return_value = []
        article_repo = MagicMock()
        article_repo.list_articles_for_stocks.return_value = ([_article(importance=Decimal("0.9"))], 1)

        usecase = GetMyHoldingsNewsToolUseCase(
            snapshot_repo=snapshot_repo,
            watchlist_repo=watchlist_repo,
            article_repo=article_repo,
        )
        usecase.execute(user_id=2, days=14, min_importance=Decimal("0.5"), limit=5)
        article_repo.list_articles_for_stocks.assert_called_once_with(
            stock_ids=[100],
            days=14,
            min_importance=Decimal("0.5"),
            limit=5,
        )
