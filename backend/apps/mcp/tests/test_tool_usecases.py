"""7 ツール UseCase の代表テスト（依存はモック）。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.get_fx_analysis_tool_usecase import (
    GetFxAnalysisToolUseCase,
)
from apps.mcp.application.usecases.tools.get_menu_usecase import (
    GetMenuToolUseCase,
)
from apps.mcp.application.usecases.tools.get_my_watchlist_usecase import (
    GetMyWatchlistToolUseCase,
)
from apps.mcp.application.usecases.tools.get_stock_financials_usecase import (
    GetStockFinancialsToolUseCase,
)
from apps.mcp.application.usecases.tools.get_stock_summary_usecase import (
    GetStockSummaryToolUseCase,
)
from apps.mcp.application.usecases.tools.search_stock_news_sources_usecase import (
    SearchStockNewsSourcesToolUseCase,
)


def _stock_entity(id_: int = 1, code: str = "7203", name: str = "トヨタ自動車") -> object:
    s = MagicMock()
    s.id = id_
    s.code = code
    s.name = name
    s.market_type = "JP"
    return s


def _screening_result() -> object:
    """ScreeningResult の最低限の属性を持つ MagicMock。"""
    r = MagicMock()
    r.code = "7203"
    r.name = "トヨタ自動車"
    r.sector = "輸送用機器"
    r.is_active = True
    r.latest_price = Decimal("2800")
    r.latest_price_date = "2026-05-13"
    r.bps = Decimal("2500")
    r.eps = Decimal("350")
    r.roe = Decimal("0.14")
    r.current_pbr = Decimal("1.12")
    r.fair_pbr = Decimal("1.35")
    r.fair_value = Decimal("3375")
    r.discount_rate = Decimal("0.17")
    r.evaluation_zone = "buy"
    r.implied_growth_rate = Decimal("0.04")
    r.growth_rate_label = "premium"
    r.eps_growth_yoy = None
    r.eps_cagr_3y = None
    r.roe_trend = "stable"
    r.price_position_52w = Decimal("0.5")
    r.near_52w_high = False
    r.distance_from_52w_high = None
    r.momentum_signal = "neutral"
    r.dividend_yield = Decimal("2.5")
    r.payout_ratio = None
    r.consecutive_dividend_years = None
    r.progressive_dividend_years = None
    r.liquidity_level = "high"
    r.not_calculable_reason = None
    return r


class TestGetStockSummaryToolUseCase:
    def test_returns_dict_with_key_fields(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = [_screening_result()]
        usecase = GetStockSummaryToolUseCase(screening_usecase=screening)
        result = usecase.execute(code="7203")
        assert result["code"] == "7203"
        assert result["fair_value"] == "3375"
        assert result["evaluation_zone"] == "buy"

    def test_not_found_raises(self) -> None:
        screening = MagicMock()
        screening.execute.return_value = []
        usecase = GetStockSummaryToolUseCase(screening_usecase=screening)
        with pytest.raises(ValueError):
            usecase.execute(code="0000")


class TestGetStockFinancialsToolUseCase:
    def test_returns_recent_financials(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = _stock_entity()
        fin = MagicMock()
        fin.fiscal_year = 2025
        fin.period_end_date = None
        fin.bps = Decimal("2500")
        fin.eps = Decimal("350")
        fin.roe = Decimal("0.14")
        fin.revenue = 30000
        fin.operating_income = 3000
        fin.operating_cash_flow = None
        fin.free_cash_flow = None
        fin.eps_forecast = None
        financial_repo = MagicMock()
        financial_repo.find_recent_by_stock_id.return_value = [fin]

        usecase = GetStockFinancialsToolUseCase(stock_repo=stock_repo, financial_repo=financial_repo)
        result = usecase.execute(code="7203", years=3)
        assert result["code"] == "7203"
        assert result["years"][0]["fiscal_year"] == 2025
        financial_repo.find_recent_by_stock_id.assert_called_once_with(1, limit=3)

    def test_unknown_code_raises(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = None
        usecase = GetStockFinancialsToolUseCase(stock_repo=stock_repo, financial_repo=MagicMock())
        with pytest.raises(ValueError):
            usecase.execute(code="0000")


class TestGetMyWatchlistToolUseCase:
    def test_returns_items(self) -> None:
        watchlist_repo = MagicMock()
        item = MagicMock()
        item.stock_code = "7203"
        item.stock_name = "トヨタ自動車"
        item.memo = "決算近い"
        watchlist_repo.find_by_user.return_value = [item]
        usecase = GetMyWatchlistToolUseCase(watchlist_repo=watchlist_repo)
        result = usecase.execute(user_id=1)
        assert result["count"] == 1
        assert result["items"][0]["code"] == "7203"


class TestGetFxAnalysisToolUseCase:
    def test_returns_dict_passthrough(self) -> None:
        fx_usecase = MagicMock()
        fx_usecase.execute.return_value = {"current_rate": "150.0"}
        usecase = GetFxAnalysisToolUseCase(fx_usecase=fx_usecase)
        assert usecase.execute() == {"current_rate": "150.0"}


class TestSearchStockNewsSourcesToolUseCase:
    def test_returns_urls(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = _stock_entity()
        url_builder = MagicMock()
        url_builder.build.return_value = [
            {"name": "日経", "url": "https://...", "tier": "secondary"},
        ]
        usecase = SearchStockNewsSourcesToolUseCase(stock_repo=stock_repo, url_builder=url_builder)
        result = usecase.execute(code="7203")
        assert result["stock_name"] == "トヨタ自動車"
        assert len(result["sources"]) == 1
        url_builder.build.assert_called_once_with(stock_name="トヨタ自動車", query=None)

    def test_query_passed_through(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = _stock_entity()
        url_builder = MagicMock()
        url_builder.build.return_value = []
        usecase = SearchStockNewsSourcesToolUseCase(stock_repo=stock_repo, url_builder=url_builder)
        usecase.execute(code="7203", query="自動運転")
        url_builder.build.assert_called_once_with(stock_name="トヨタ自動車", query="自動運転")

    def test_unknown_code_raises(self) -> None:
        stock_repo = MagicMock()
        stock_repo.find_by_code.return_value = None
        usecase = SearchStockNewsSourcesToolUseCase(stock_repo=stock_repo, url_builder=MagicMock())
        with pytest.raises(ValueError):
            usecase.execute(code="0000")


class TestGetMenuToolUseCase:
    """会話メニュー UseCase のテスト。"""

    def _make(self, holdings_result: dict[str, Any] | None = None) -> GetMenuToolUseCase:
        holdings_usecase = MagicMock()
        holdings_usecase.execute.return_value = holdings_result or {"holdings": []}
        return GetMenuToolUseCase(holdings_usecase=holdings_usecase)

    def test_root_level_returns_options(self) -> None:
        usecase = self._make()
        result = usecase.execute(level="root")
        assert result["level"] == "root"
        assert "何をしたいですか" in result["title"]
        assert len(result["options"]) >= 5
        assert any(o["id"] == "stock_analysis" for o in result["options"])
        assert "display_markdown" in result
        assert result["display_markdown"].startswith("## ")

    def test_intermediate_level_chains_next_menu(self) -> None:
        usecase = self._make()
        result = usecase.execute(level="stock_analysis_kind")
        assert result["level"] == "stock_analysis_kind"
        evaluation = next(o for o in result["options"] if o["id"] == "evaluation")
        assert evaluation["next_menu"] == "pick_stock"
        assert evaluation["params"]["then_tool"] == "get_stock_summary"

    def test_pick_stock_dynamic_holdings_with_then_tool(self) -> None:
        holdings = {
            "holdings": [
                {"stock_code": "5892", "name": "yutori", "asset_type": "stock"},
                {"stock_code": "7203", "name": "トヨタ自動車", "asset_type": "stock"},
                # 重複は排除されること
                {"stock_code": "5892", "name": "yutori (別口座)", "asset_type": "stock"},
                # stock 以外は除外されること
                {"stock_code": "1306", "name": "TOPIX 連動", "asset_type": "etf"},
            ]
        }
        usecase = self._make(holdings_result=holdings)
        result = usecase.execute(
            level="pick_stock",
            user_id=42,
            context='{"then_tool": "get_stock_risk_tags"}',
        )
        codes = [o["id"] for o in result["options"]]
        assert "5892" in codes
        assert "7203" in codes
        # ETF は除外
        assert "1306" not in codes
        # 末尾には "その他" がある
        assert result["options"][-1]["id"] == "other"
        # then_tool が各 option に差し込まれる
        yutori = next(o for o in result["options"] if o["id"] == "5892")
        assert yutori["next_tool"] == "get_stock_risk_tags"
        assert yutori["params"] == {"code": "5892"}

    def test_pick_stock_requires_auth(self) -> None:
        usecase = self._make()
        with pytest.raises(PermissionError):
            usecase.execute(level="pick_stock", user_id=None)

    def test_invalid_level_raises(self) -> None:
        from apps.mcp.domain.exceptions import McpToolNotFoundError

        usecase = self._make()
        with pytest.raises(McpToolNotFoundError):
            usecase.execute(level="not_a_real_menu")

    def test_invalid_context_json_is_ignored(self) -> None:
        holdings = {
            "holdings": [
                {"stock_code": "5892", "name": "yutori", "asset_type": "stock"},
            ]
        }
        usecase = self._make(holdings_result=holdings)
        # context が壊れていても落ちず、then_tool なしで動くこと
        result = usecase.execute(level="pick_stock", user_id=1, context="not-json")
        yutori = next(o for o in result["options"] if o["id"] == "5892")
        assert "next_tool" not in yutori
