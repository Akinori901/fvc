"""割安株スクリーニングAPIビュー。"""

import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
from config.container import (
    dividend_repository,
    financial_repository,
    margin_repository,
    owner_shareholder_repository,
    price_repository,
    stock_repository,
)


class ScreeningView(APIView):
    """GET /api/stocks/screening/ — 全銘柄スクリーニング"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        # キャッシュキー生成
        params_key = hashlib.md5(
            json.dumps(sorted(request.query_params.items()), ensure_ascii=False).encode()
        ).hexdigest()
        cache_key = f"screening:v1:{params_key}"

        # キャッシュ確認
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        growth_rate = _parse_decimal(request.query_params.get("growth_rate"), Decimal("0.05"))
        min_discount = _parse_decimal_or_none(request.query_params.get("min_discount"))
        sector = request.query_params.get("sector") or None
        market_type = request.query_params.get("market_type", "JP")
        include_inactive = request.query_params.get("include_inactive", "false").lower() == "true"
        min_eps_growth_yoy = _parse_decimal_or_none(request.query_params.get("min_eps_growth_yoy"))
        min_eps_cagr_3y = _parse_decimal_or_none(request.query_params.get("min_eps_cagr_3y"))
        roe_trend_filter = request.query_params.get("roe_trend") or None
        min_roe = _parse_decimal_or_none(request.query_params.get("min_roe"))
        max_sl_ratio = _parse_decimal_or_none(request.query_params.get("max_sl_ratio"))
        min_dividend_yield = _parse_decimal_or_none(request.query_params.get("min_dividend_yield"))
        max_payout_ratio = _parse_decimal_or_none(request.query_params.get("max_payout_ratio"))
        min_consecutive_dividend_years = _parse_int_or_none(request.query_params.get("min_consecutive_dividend_years"))
        min_progressive_dividend_years = _parse_int_or_none(request.query_params.get("min_progressive_dividend_years"))
        min_liquidity_level = request.query_params.get("min_liquidity_level") or None
        min_momentum_signal = request.query_params.get("min_momentum_signal") or None
        owner_managed_only = request.query_params.get("owner_managed_only", "false").lower() == "true"
        min_fcf_yield = _parse_decimal_or_none(request.query_params.get("min_fcf_yield"))
        # 信用買残トレンド（1〜12ヶ月）
        margin_trend_months = _parse_int_or_none(request.query_params.get("margin_trend_months"))
        if margin_trend_months is not None and not 1 <= margin_trend_months <= 12:  # noqa: PLR2004
            margin_trend_months = None
        long_balance_trend = request.query_params.get("long_balance_trend") or None
        if long_balance_trend not in ("increasing", "decreasing", None):
            long_balance_trend = None
        margin_trend_threshold_pct = _parse_decimal_or_none(request.query_params.get("margin_trend_threshold_pct"))
        if margin_trend_threshold_pct is not None:
            margin_trend_threshold_pct = abs(margin_trend_threshold_pct)
        # トレンド指定があるのに期間が無い場合は既定 2ヶ月とする
        if long_balance_trend is not None and margin_trend_months is None:
            margin_trend_months = 2

        usecase = ScreeningUseCase(
            stock_repo=stock_repository(),
            financial_repo=financial_repository(),
            margin_repo=margin_repository(),
            price_repo=price_repository(),
            dividend_repo=dividend_repository(),
            owner_repo=owner_shareholder_repository(),
        )
        results = usecase.execute(
            growth_rate=growth_rate,
            market_type=market_type,
            sector=sector,
            min_discount=min_discount,
            include_inactive=include_inactive,
            min_eps_growth_yoy=min_eps_growth_yoy,
            min_eps_cagr_3y=min_eps_cagr_3y,
            roe_trend_filter=roe_trend_filter,
            min_roe=min_roe,
            max_sl_ratio=max_sl_ratio,
            min_dividend_yield=min_dividend_yield,
            max_payout_ratio=max_payout_ratio,
            min_consecutive_dividend_years=min_consecutive_dividend_years,
            min_progressive_dividend_years=min_progressive_dividend_years,
            min_liquidity_level=min_liquidity_level,
            min_momentum_signal=min_momentum_signal,
            owner_managed_only=owner_managed_only,
            min_fcf_yield=min_fcf_yield,
            margin_trend_months=margin_trend_months,
            long_balance_trend=long_balance_trend,
            margin_trend_threshold_pct=margin_trend_threshold_pct,
        )

        def _s(v: object) -> str | None:
            return str(v) if v is not None else None

        data: list[dict[str, object]] = [
            {
                "code": r.code,
                "name": r.name,
                "sector": r.sector,
                "latest_price": _s(r.latest_price),
                "latest_price_date": r.latest_price_date,
                "bps": _s(r.bps),
                "eps": _s(r.eps),
                "roe": _s(r.roe),
                "fair_pbr": _s(r.fair_pbr),
                "fair_value": _s(r.fair_value),
                "discount_rate": _s(r.discount_rate),
                "evaluation_zone": r.evaluation_zone,
                "current_pbr": _s(r.current_pbr),
                "implied_growth_rate": _s(r.implied_growth_rate),
                "growth_rate_label": r.growth_rate_label,
                "company_forecast_growth_rate": _s(r.company_forecast_growth_rate),
                "is_active": r.is_active,
                "not_calculable_reason": r.not_calculable_reason,
                "is_manual_financial": r.is_manual_financial,
                "eps_growth_yoy": _s(r.eps_growth_yoy),
                "eps_cagr_3y": _s(r.eps_cagr_3y),
                "roe_trend": r.roe_trend,
                "revenue_growth_yoy": _s(r.revenue_growth_yoy),
                "op_income_growth_yoy": _s(r.op_income_growth_yoy),
                "sl_ratio": _s(r.sl_ratio),
                "long_balance": r.long_balance,
                "short_balance": r.short_balance,
                "long_balance_change": r.long_balance_change,
                "long_balance_change_pct": _s(r.long_balance_change_pct),
                "long_balance_trend": r.long_balance_trend,
                "price_position_52w": _s(r.price_position_52w),
                "near_52w_high": r.near_52w_high,
                "distance_from_52w_high": _s(r.distance_from_52w_high),
                "volume_ratio_20d": _s(r.volume_ratio_20d),
                "ma_25_deviation": _s(r.ma_25_deviation),
                "momentum_signal": r.momentum_signal,
                "avg_turnover_20d": _s(r.avg_turnover_20d),
                "liquidity_level": r.liquidity_level,
                "dividend_yield": _s(r.dividend_yield),
                "payout_ratio": _s(r.payout_ratio),
                "consecutive_dividend_years": r.consecutive_dividend_years,
                "progressive_dividend_years": r.progressive_dividend_years,
                "dividend_score": r.dividend_score,
                "fcf": r.fcf,
                "fcf_yield": _s(r.fcf_yield),
                "fcf_margin": _s(r.fcf_margin),
                "fcf_score": r.fcf_score,
                "is_owner_managed": r.is_owner_managed,
                "owner_ratio": _s(r.owner_ratio),
                "owner_match_type": r.owner_match_type,
            }
            for r in results
        ]
        # キャッシュに保存
        cache.set(cache_key, data, timeout=1800)  # 30分
        return Response(data)


def _parse_decimal(value: str | None, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(value)
    except InvalidOperation:
        return default


def _parse_int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None
