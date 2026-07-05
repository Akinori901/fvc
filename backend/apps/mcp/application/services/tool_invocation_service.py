"""MCP ツールのディスパッチャ。

REST View / MCP server の両方から呼ばれる共通エントリポイント。
ツール名 + パラメータ + user_id を受け取り、対応する UseCase を呼び結果 dict を返す。
"""

from __future__ import annotations

from typing import Any

from ...domain.exceptions import McpToolNotFoundError

# ツール名定数
TOOL_GET_STOCK_SUMMARY = "get_stock_summary"
TOOL_GET_STOCK_FINANCIALS = "get_stock_financials"
TOOL_GET_MY_HOLDINGS = "get_my_holdings"
TOOL_GET_MY_WATCHLIST = "get_my_watchlist"
TOOL_GET_FX_ANALYSIS = "get_fx_analysis"
TOOL_GET_EARNINGS_CALENDAR = "get_earnings_calendar"
TOOL_SEARCH_STOCK_NEWS_SOURCES = "search_stock_news_sources"
TOOL_GET_MY_PORTFOLIO_SUMMARY = "get_my_portfolio_summary"
TOOL_GET_MY_PNL = "get_my_pnl"
TOOL_GET_MARGIN_BALANCE = "get_margin_balance"
TOOL_GET_MY_HOLDINGS_NEWS = "get_my_holdings_news"
TOOL_GET_SCREENING_CANDIDATES = "get_screening_candidates"
TOOL_GET_SELL_CANDIDATES = "get_sell_candidates"
TOOL_GET_STOCK_RISK_TAGS = "get_stock_risk_tags"
TOOL_GET_STOCK_OPPORTUNITY_TAGS = "get_stock_opportunity_tags"
TOOL_GET_PRICE_MOVERS = "get_price_movers"
TOOL_GET_MY_MARGIN_POSITIONS = "get_my_margin_positions"
TOOL_GET_MY_HOLDINGS_ALERTS = "get_my_holdings_alerts"
TOOL_GET_MY_DIVIDENDS_CALENDAR = "get_my_dividends_calendar"
TOOL_SAVE_AI_DECISION = "save_ai_decision"
TOOL_GET_PRICE_DISTRIBUTION_3M = "get_price_distribution_3m"
TOOL_SEARCH_TICKER = "search_ticker"
TOOL_GET_MENU = "get_menu"

ALL_TOOLS = (
    TOOL_GET_STOCK_SUMMARY,
    TOOL_GET_STOCK_FINANCIALS,
    TOOL_GET_MY_HOLDINGS,
    TOOL_GET_MY_WATCHLIST,
    TOOL_GET_FX_ANALYSIS,
    TOOL_GET_EARNINGS_CALENDAR,
    TOOL_SEARCH_STOCK_NEWS_SOURCES,
    TOOL_GET_MY_PORTFOLIO_SUMMARY,
    TOOL_GET_MY_PNL,
    TOOL_GET_MARGIN_BALANCE,
    TOOL_GET_MY_HOLDINGS_NEWS,
    TOOL_GET_SCREENING_CANDIDATES,
    TOOL_GET_SELL_CANDIDATES,
    TOOL_GET_STOCK_RISK_TAGS,
    TOOL_GET_STOCK_OPPORTUNITY_TAGS,
    TOOL_GET_PRICE_MOVERS,
    TOOL_GET_MY_MARGIN_POSITIONS,
    TOOL_GET_MY_HOLDINGS_ALERTS,
    TOOL_GET_MY_DIVIDENDS_CALENDAR,
    TOOL_SAVE_AI_DECISION,
    TOOL_GET_PRICE_DISTRIBUTION_3M,
    TOOL_SEARCH_TICKER,
    TOOL_GET_MENU,
)

# 認証が必須なツール（user_id が None の場合はエラー）
# get_margin_balance / get_screening_candidates / get_stock_*_tags / get_price_movers /
# get_price_distribution_3m は公開情報のため認証不要
USER_REQUIRED_TOOLS = frozenset(
    {
        TOOL_GET_MY_HOLDINGS,
        TOOL_GET_MY_WATCHLIST,
        TOOL_GET_MY_PORTFOLIO_SUMMARY,
        TOOL_GET_MY_PNL,
        TOOL_GET_MY_HOLDINGS_NEWS,
        TOOL_GET_SELL_CANDIDATES,
        TOOL_GET_MY_MARGIN_POSITIONS,
        TOOL_GET_MY_HOLDINGS_ALERTS,
        TOOL_GET_MY_DIVIDENDS_CALENDAR,
        TOOL_SAVE_AI_DECISION,
    }
)


class ToolInvocationService:
    """ツール名から UseCase を解決して実行する単一責任サービス。"""

    def invoke(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if tool_name not in ALL_TOOLS:
            raise McpToolNotFoundError(f"未知のツール: {tool_name}")

        if tool_name in USER_REQUIRED_TOOLS and user_id is None:
            raise PermissionError(f"ツール '{tool_name}' には認証が必要です")

        # ローカルインポート（循環参照防止 + Django app ready 後に評価）
        from config import container

        if tool_name == TOOL_GET_STOCK_SUMMARY:
            return container.get_stock_summary_tool_usecase().execute(code=str(params["code"]))

        if tool_name == TOOL_GET_STOCK_FINANCIALS:
            return container.get_stock_financials_tool_usecase().execute(
                code=str(params["code"]),
                years=int(params.get("years", 5)),
            )

        if tool_name == TOOL_GET_MY_HOLDINGS:
            assert user_id is not None
            return container.get_my_holdings_tool_usecase().execute(user_id=user_id)

        if tool_name == TOOL_GET_MY_WATCHLIST:
            assert user_id is not None
            return container.get_my_watchlist_tool_usecase().execute(user_id=user_id)

        if tool_name == TOOL_GET_FX_ANALYSIS:
            return container.get_fx_analysis_tool_usecase().execute()

        if tool_name == TOOL_GET_EARNINGS_CALENDAR:
            codes_raw = params.get("codes")
            codes: list[str] | None
            if codes_raw is None or codes_raw == "":
                codes = None
            elif isinstance(codes_raw, str):
                codes = [c.strip() for c in codes_raw.split(",") if c.strip()]
            else:
                codes = [str(c) for c in codes_raw]
            return container.get_earnings_calendar_tool_usecase().execute(
                codes=codes,
                days_ahead=int(params.get("days_ahead", 30)),
            )

        if tool_name == TOOL_SEARCH_STOCK_NEWS_SOURCES:
            query_param = params.get("query")
            query_str: str | None = str(query_param) if query_param else None
            return container.search_stock_news_sources_tool_usecase().execute(code=str(params["code"]), query=query_str)

        if tool_name == TOOL_GET_MY_PORTFOLIO_SUMMARY:
            assert user_id is not None
            return container.get_my_portfolio_summary_tool_usecase().execute(user_id=user_id)

        if tool_name == TOOL_GET_MY_PNL:
            assert user_id is not None
            code_param = params.get("code")
            code_str: str | None = str(code_param) if code_param else None
            return container.get_my_pnl_tool_usecase().execute(user_id=user_id, code=code_str)

        if tool_name == TOOL_GET_MARGIN_BALANCE:
            return container.get_margin_balance_tool_usecase().execute(code=str(params["code"]))

        if tool_name == TOOL_GET_MY_HOLDINGS_NEWS:
            from decimal import Decimal

            assert user_id is not None
            min_importance_raw = params.get("min_importance")
            min_importance: Decimal | None
            if min_importance_raw is None or min_importance_raw == "":
                min_importance = None
            else:
                min_importance = Decimal(str(min_importance_raw))
            return container.get_my_holdings_news_tool_usecase().execute(
                user_id=user_id,
                days=int(params.get("days", 7)),
                min_importance=min_importance,
                limit=int(params.get("limit", 20)),
            )

        if tool_name == TOOL_GET_SCREENING_CANDIDATES:
            from decimal import Decimal

            include_zones_raw = params.get("include_zones")
            include_zones: list[str] | None
            if include_zones_raw is None or include_zones_raw == "":
                include_zones = None
            elif isinstance(include_zones_raw, str):
                include_zones = [z.strip() for z in include_zones_raw.split(",") if z.strip()]
            else:
                include_zones = [str(z) for z in include_zones_raw]

            exclude_codes_raw = params.get("exclude_codes")
            exclude_codes: list[str] | None
            if exclude_codes_raw is None or exclude_codes_raw == "":
                exclude_codes = None
            elif isinstance(exclude_codes_raw, str):
                exclude_codes = [c.strip() for c in exclude_codes_raw.split(",") if c.strip()]
            else:
                exclude_codes = [str(c) for c in exclude_codes_raw]

            return container.get_screening_candidates_tool_usecase().execute(
                growth_rate=_optional_decimal(params.get("growth_rate")),
                max_pbr_ratio=_optional_decimal(params.get("max_pbr_ratio")),
                min_roe=_optional_decimal(params.get("min_roe")),
                include_zones=include_zones,
                min_momentum_signal=(str(params["min_momentum_signal"]) if params.get("min_momentum_signal") else None),
                exclude_codes=exclude_codes,
                limit=int(params.get("limit", 20)),
                market_type=str(params.get("market_type", "JP")),
            )

        if tool_name == TOOL_GET_SELL_CANDIDATES:
            assert user_id is not None
            return container.get_sell_candidates_tool_usecase().execute(user_id=user_id)

        if tool_name == TOOL_GET_STOCK_RISK_TAGS:
            return container.get_stock_risk_tags_tool_usecase().execute(code=str(params["code"]))

        if tool_name == TOOL_GET_STOCK_OPPORTUNITY_TAGS:
            return container.get_stock_opportunity_tags_tool_usecase().execute(code=str(params["code"]))

        if tool_name == TOOL_GET_PRICE_MOVERS:
            import datetime

            target_date: datetime.date | None = None
            date_raw = params.get("date")
            if date_raw:
                target_date = datetime.date.fromisoformat(str(date_raw))
            return container.get_price_movers_tool_usecase().execute(
                direction=str(params.get("direction", "both")),
                scope=str(params.get("scope", "all")),
                threshold_pct=_optional_decimal(params.get("threshold_pct")),
                min_volume_ratio=_optional_decimal(params.get("min_volume_ratio")),
                include_limit_hits=_parse_bool(params.get("include_limit_hits"), default=True),
                limit=int(params.get("limit", 20)),
                target_date=target_date,
                user_id=user_id,
            )

        if tool_name == TOOL_GET_MY_MARGIN_POSITIONS:
            assert user_id is not None
            return container.get_my_margin_positions_tool_usecase().execute(user_id=user_id)

        if tool_name == TOOL_GET_MY_HOLDINGS_ALERTS:
            assert user_id is not None
            return container.get_my_holdings_alerts_tool_usecase().execute(
                user_id=user_id,
                severity_min=str(params.get("severity_min", "low")),
            )

        if tool_name == TOOL_GET_MY_DIVIDENDS_CALENDAR:
            assert user_id is not None
            return container.get_my_dividends_calendar_tool_usecase().execute(
                user_id=user_id,
                months_ahead=int(params.get("months_ahead", 3)),
            )

        if tool_name == TOOL_SAVE_AI_DECISION:
            assert user_id is not None
            return container.save_ai_decision_tool_usecase().execute(
                user_id=user_id,
                code=str(params["code"]),
                decision_type=str(params["decision_type"]),
                rationale=str(params.get("rationale", "")),
                confidence=_optional_decimal(params.get("confidence")),
                ai_model=str(params.get("ai_model", "")),
            )

        if tool_name == TOOL_GET_PRICE_DISTRIBUTION_3M:
            rng_seed_raw = params.get("rng_seed")
            rng_seed = _optional_int(rng_seed_raw)
            return container.get_price_distribution_3m_tool_usecase().execute(
                code=str(params["code"]),
                horizon_days=int(params.get("horizon_days", 90)),
                simulation_runs=int(params.get("simulation_runs", 10000)),
                lookback_days=int(params.get("lookback_days", 252)),
                rng_seed=rng_seed,
            )

        if tool_name == TOOL_SEARCH_TICKER:
            market_type_raw = params.get("market_type")
            market_type_str: str | None = str(market_type_raw) if market_type_raw else None
            return container.search_ticker_tool_usecase().execute(
                query=str(params.get("query", "")),
                instrument_type=str(params.get("instrument_type", "all")),
                market_type=market_type_str,
                limit=int(params.get("limit", 10)),
            )

        if tool_name == TOOL_GET_MENU:
            level_raw = params.get("level")
            context_raw = params.get("context")
            context_str: str | None
            if context_raw is None or context_raw == "":
                context_str = None
            elif isinstance(context_raw, str):
                context_str = context_raw
            else:
                # dict 等が来たら JSON 文字列化して UseCase に渡す
                import json as _json

                context_str = _json.dumps(context_raw)
            return container.get_menu_tool_usecase().execute(
                level=str(level_raw) if level_raw else "root",
                context=context_str,
                user_id=user_id,
            )

        # ここには到達しない（ALL_TOOLS でガード済み）
        raise McpToolNotFoundError(tool_name)


def _parse_bool(raw: Any, default: bool = False) -> bool:
    """REST のクエリ文字列 ('true'/'false'/'1'/'0') と Python の bool / None を吸収する。"""
    if raw is None or raw == "":
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("true", "1", "yes", "on")


def _optional_decimal(raw: Any) -> Any:
    """空文字 / None でないときだけ Decimal に変換する。"""
    from decimal import Decimal

    if raw is None or raw == "":
        return None
    return Decimal(str(raw))


def _optional_int(raw: Any) -> int | None:
    """空文字 / None でないときだけ int に変換する。"""
    if raw is None or raw == "":
        return None
    return int(raw)
