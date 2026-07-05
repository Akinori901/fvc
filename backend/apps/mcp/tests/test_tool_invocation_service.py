"""ToolInvocationService の単体テスト（ディスパッチロジック）。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.mcp.application.services.tool_invocation_service import (
    ALL_TOOLS,
    USER_REQUIRED_TOOLS,
    ToolInvocationService,
)
from apps.mcp.domain.exceptions import McpToolNotFoundError


class TestToolInvocationService:
    def setup_method(self) -> None:
        self.service = ToolInvocationService()

    def test_unknown_tool_raises(self) -> None:
        with pytest.raises(McpToolNotFoundError):
            self.service.invoke("nope", {})

    def test_user_required_tool_without_user_raises(self) -> None:
        for tool in USER_REQUIRED_TOOLS:
            with pytest.raises(PermissionError):
                self.service.invoke(tool, {})

    def test_all_tools_set_includes_twenty_three_entries(self) -> None:
        assert len(ALL_TOOLS) == 23

    def test_dispatches_get_stock_summary(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"code": "7203"}
        with patch("config.container.get_stock_summary_tool_usecase", return_value=mock_usecase):
            result = self.service.invoke("get_stock_summary", {"code": "7203"})
        assert result == {"code": "7203"}
        mock_usecase.execute.assert_called_once_with(code="7203")

    def test_dispatches_get_stock_financials_with_default_years(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"code": "7203", "years": []}
        with patch("config.container.get_stock_financials_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_stock_financials", {"code": "7203"})
        mock_usecase.execute.assert_called_once_with(code="7203", years=5)

    def test_dispatches_get_my_holdings_with_user(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"holdings": []}
        with patch("config.container.get_my_holdings_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_holdings", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42)

    def test_earnings_calendar_codes_csv_parsed(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"events": []}
        with patch("config.container.get_earnings_calendar_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_earnings_calendar", {"codes": "7203,6758", "days_ahead": 14})
        mock_usecase.execute.assert_called_once_with(codes=["7203", "6758"], days_ahead=14)

    def test_earnings_calendar_empty_codes_becomes_none(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"events": []}
        with patch("config.container.get_earnings_calendar_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_earnings_calendar", {})
        mock_usecase.execute.assert_called_once_with(codes=None, days_ahead=30)

    def test_dispatches_get_my_portfolio_summary_with_user(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"total_value": "1000"}
        with patch("config.container.get_my_portfolio_summary_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_portfolio_summary", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42)

    def test_dispatches_get_my_pnl_with_optional_code(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"holdings": []}
        with patch("config.container.get_my_pnl_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_pnl", {"code": "5892"}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42, code="5892")

    def test_dispatches_get_my_pnl_without_code(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"holdings": []}
        with patch("config.container.get_my_pnl_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_pnl", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42, code=None)

    def test_dispatches_get_margin_balance_without_user(self) -> None:
        """get_margin_balance は公開情報のため user_id 不要。"""
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"code": "5892"}
        with patch("config.container.get_margin_balance_tool_usecase", return_value=mock_usecase):
            result = self.service.invoke("get_margin_balance", {"code": "5892"})
        assert result == {"code": "5892"}
        mock_usecase.execute.assert_called_once_with(code="5892")

    def test_dispatches_get_my_holdings_news_with_filters(self) -> None:
        from decimal import Decimal

        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"articles": []}
        with patch("config.container.get_my_holdings_news_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_my_holdings_news",
                {"days": 14, "min_importance": "0.5", "limit": 5},
                user_id=42,
            )
        mock_usecase.execute.assert_called_once_with(
            user_id=42,
            days=14,
            min_importance=Decimal("0.5"),
            limit=5,
        )

    def test_dispatches_get_my_holdings_news_with_defaults(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"articles": []}
        with patch("config.container.get_my_holdings_news_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_holdings_news", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42, days=7, min_importance=None, limit=20)

    def test_dispatches_get_screening_candidates_with_csv_params(self) -> None:
        from decimal import Decimal

        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"count": 0, "candidates": []}
        with patch("config.container.get_screening_candidates_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_screening_candidates",
                {
                    "growth_rate": "0.03",
                    "max_pbr_ratio": "1.0",
                    "include_zones": "cheap,very_cheap",
                    "exclude_codes": "5892,7203",
                    "limit": 10,
                },
            )
        mock_usecase.execute.assert_called_once_with(
            growth_rate=Decimal("0.03"),
            max_pbr_ratio=Decimal("1.0"),
            min_roe=None,
            include_zones=["cheap", "very_cheap"],
            min_momentum_signal=None,
            exclude_codes=["5892", "7203"],
            limit=10,
            market_type="JP",
        )

    def test_dispatches_get_sell_candidates_with_user(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"candidates": []}
        with patch("config.container.get_sell_candidates_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_sell_candidates", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42)

    def test_dispatches_get_stock_risk_tags(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"risk_tags": []}
        with patch("config.container.get_stock_risk_tags_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_stock_risk_tags", {"code": "5892"})
        mock_usecase.execute.assert_called_once_with(code="5892")

    def test_dispatches_get_stock_opportunity_tags(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"opportunity_tags": []}
        with patch("config.container.get_stock_opportunity_tags_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_stock_opportunity_tags", {"code": "5892"})
        mock_usecase.execute.assert_called_once_with(code="5892")

    def test_dispatches_get_price_movers_with_all_params(self) -> None:
        import datetime
        from decimal import Decimal

        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"gainers": [], "losers": []}
        with patch("config.container.get_price_movers_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_price_movers",
                {
                    "direction": "gainers",
                    "scope": "my_watchlist",
                    "threshold_pct": "10",
                    "min_volume_ratio": "2.0",
                    "include_limit_hits": "true",
                    "limit": 5,
                    "date": "2026-05-15",
                },
                user_id=42,
            )
        mock_usecase.execute.assert_called_once_with(
            direction="gainers",
            scope="my_watchlist",
            threshold_pct=Decimal("10"),
            min_volume_ratio=Decimal("2.0"),
            include_limit_hits=True,
            limit=5,
            target_date=datetime.date(2026, 5, 15),
            user_id=42,
        )

    def test_dispatches_get_price_movers_with_defaults(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"gainers": [], "losers": []}
        with patch("config.container.get_price_movers_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_price_movers", {})
        mock_usecase.execute.assert_called_once_with(
            direction="both",
            scope="all",
            threshold_pct=None,
            min_volume_ratio=None,
            include_limit_hits=True,
            limit=20,
            target_date=None,
            user_id=None,
        )

    def test_dispatches_get_my_margin_positions_with_user(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"positions": []}
        with patch("config.container.get_my_margin_positions_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_margin_positions", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42)

    def test_dispatches_get_my_holdings_alerts_with_severity(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"alerts": []}
        with patch("config.container.get_my_holdings_alerts_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_my_holdings_alerts",
                {"severity_min": "high"},
                user_id=42,
            )
        mock_usecase.execute.assert_called_once_with(user_id=42, severity_min="high")

    def test_dispatches_get_my_holdings_alerts_with_default_severity(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"alerts": []}
        with patch("config.container.get_my_holdings_alerts_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_holdings_alerts", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42, severity_min="low")

    def test_dispatches_get_my_dividends_calendar_with_months_ahead(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"upcoming": []}
        with patch("config.container.get_my_dividends_calendar_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_my_dividends_calendar",
                {"months_ahead": 6},
                user_id=42,
            )
        mock_usecase.execute.assert_called_once_with(user_id=42, months_ahead=6)

    def test_dispatches_get_my_dividends_calendar_with_default(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"upcoming": []}
        with patch("config.container.get_my_dividends_calendar_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_my_dividends_calendar", {}, user_id=42)
        mock_usecase.execute.assert_called_once_with(user_id=42, months_ahead=3)

    def test_dispatches_save_ai_decision_with_all_params(self) -> None:
        from decimal import Decimal

        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"id": 1}
        with patch("config.container.save_ai_decision_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "save_ai_decision",
                {
                    "code": "7203",
                    "decision_type": "buy",
                    "rationale": "Strong",
                    "confidence": "0.8",
                    "ai_model": "claude-4.5-sonnet",
                },
                user_id=42,
            )
        mock_usecase.execute.assert_called_once_with(
            user_id=42,
            code="7203",
            decision_type="buy",
            rationale="Strong",
            confidence=Decimal("0.8"),
            ai_model="claude-4.5-sonnet",
        )

    def test_dispatches_get_price_distribution_3m_with_defaults(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"percentiles": {}}
        with patch("config.container.get_price_distribution_3m_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_price_distribution_3m", {"code": "7203"})
        mock_usecase.execute.assert_called_once_with(
            code="7203",
            horizon_days=90,
            simulation_runs=10000,
            lookback_days=252,
            rng_seed=None,
        )

    def test_dispatches_get_price_distribution_3m_with_rng_seed(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {}
        with patch("config.container.get_price_distribution_3m_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_price_distribution_3m",
                {"code": "7203", "rng_seed": 42, "simulation_runs": 500},
            )
        mock_usecase.execute.assert_called_once_with(
            code="7203",
            horizon_days=90,
            simulation_runs=500,
            lookback_days=252,
            rng_seed=42,
        )

    def test_dispatches_search_ticker_with_defaults(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"count": 0, "query": "yutori", "items": []}
        with patch("config.container.search_ticker_tool_usecase", return_value=mock_usecase):
            self.service.invoke("search_ticker", {"query": "yutori"})
        mock_usecase.execute.assert_called_once_with(
            query="yutori",
            instrument_type="all",
            market_type=None,
            limit=10,
        )

    def test_dispatches_search_ticker_with_all_params(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"count": 0, "query": "AAPL", "items": []}
        with patch("config.container.search_ticker_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "search_ticker",
                {
                    "query": "AAPL",
                    "instrument_type": "stock",
                    "market_type": "US",
                    "limit": 25,
                },
            )
        mock_usecase.execute.assert_called_once_with(
            query="AAPL",
            instrument_type="stock",
            market_type="US",
            limit=25,
        )

    def test_dispatches_get_menu_with_defaults(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"level": "root", "options": []}
        with patch("config.container.get_menu_tool_usecase", return_value=mock_usecase):
            self.service.invoke("get_menu", {})
        mock_usecase.execute.assert_called_once_with(level="root", context=None, user_id=None)

    def test_dispatches_get_menu_serializes_dict_context(self) -> None:
        mock_usecase = MagicMock()
        mock_usecase.execute.return_value = {"level": "pick_stock", "options": []}
        with patch("config.container.get_menu_tool_usecase", return_value=mock_usecase):
            self.service.invoke(
                "get_menu",
                {"level": "pick_stock", "context": {"then_tool": "get_stock_summary"}},
                user_id=7,
            )
        kwargs = mock_usecase.execute.call_args.kwargs
        assert kwargs["level"] == "pick_stock"
        assert kwargs["user_id"] == 7
        # dict は JSON 文字列化される
        import json as _json

        assert _json.loads(kwargs["context"]) == {"then_tool": "get_stock_summary"}

    def test_get_menu_is_not_user_required(self) -> None:
        """root メニューは未認証でも呼べる必要があるので USER_REQUIRED に含まれない。"""
        assert "get_menu" not in USER_REQUIRED_TOOLS
