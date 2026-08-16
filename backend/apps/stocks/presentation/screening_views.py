"""割安株スクリーニングAPIビュー。

事前計算スナップショット(t_screening_snapshots)を起点に、リクエストの growth_rate
から評価系だけを軽量再計算し、サーバーサイドでフィルタ・ソート・ページングして返す。
スナップショットが空/古い場合は従来のオンザフライ計算にフォールバックする。
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
from apps.stocks.domain.screening_snapshot_service import apply_growth_rate
from apps.stocks.models import ScreeningSnapshot
from config.container import (
    dividend_repository,
    financial_repository,
    margin_repository,
    owner_shareholder_repository,
    price_repository,
    stock_repository,
)

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.stocks.application.usecases.screening_usecase import ScreeningResult

# スナップショットがこの時間より古い/存在しない場合はオンザフライ計算にフォールバック
_SNAPSHOT_MAX_AGE = timedelta(hours=30)
_DEFAULT_LIMIT = 25
_MAX_LIMIT = 100
_LIQUIDITY_ORDER = {"very_low": 0, "low": 1, "medium": 2, "high": 3}
_MOMENTUM_ORDER = {"sell": 0, "caution": 1, "neutral": 2, "buy": 3, "strong_buy": 4}
# ソート可能な列（growth_rate 非依存はDB値、依存は軽計算値）
_SORTABLE = {"overall_score", "discount_rate", "roe", "dividend_yield", "fcf_yield", "sl_ratio"}


class ScreeningView(APIView):
    """GET /api/stocks/screening/ — 全銘柄スクリーニング（ページング）"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        q = request.query_params
        growth_rate = _parse_decimal(q.get("growth_rate"), Decimal("0.05"))
        market_type = q.get("market_type", "JP")
        include_inactive = q.get("include_inactive", "false").lower() == "true"

        # ページング/ソート/検索
        limit = max(1, min(_parse_int(q.get("limit"), _DEFAULT_LIMIT), _MAX_LIMIT))
        offset = max(0, _parse_int(q.get("offset"), 0))
        sort_by: str = q.get("sort_by", "overall_score")
        if sort_by not in _SORTABLE:
            sort_by = "overall_score"
        order_desc = q.get("order", "desc").lower() != "asc"
        search = (q.get("search") or "").strip()
        min_overall_score = _parse_int_or_none(q.get("min_overall_score"))
        min_discount = _parse_decimal_or_none(q.get("min_discount"))

        latest = ScreeningSnapshot.objects.order_by("-generated_at").values_list("generated_at", flat=True).first()
        fresh = latest is not None and (timezone.now() - latest) <= _SNAPSHOT_MAX_AGE
        if not fresh or latest is None:
            return self._fallback(request, growth_rate, market_type, include_inactive, limit, offset)

        # --- スナップショット経路 ---
        qs = ScreeningSnapshot.objects.filter(market_type=market_type)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if q.get("sector"):
            qs = qs.filter(sector=q.get("sector"))
        if search:
            from django.db.models import Q

            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        # growth_rate 非依存フィルタ（DB段で絞る）
        _min_roe = _parse_decimal_or_none(q.get("min_roe"))
        if _min_roe is not None:
            qs = qs.filter(roe__gte=_min_roe)
        _max_sl = _parse_decimal_or_none(q.get("max_sl_ratio"))
        if _max_sl is not None:
            qs = qs.filter(sl_ratio__isnull=False, sl_ratio__lte=_max_sl)
        if q.get("roe_trend"):
            qs = qs.filter(roe_trend=q.get("roe_trend"))
        _min_dy = _parse_decimal_or_none(q.get("min_dividend_yield"))
        if _min_dy is not None:
            qs = qs.filter(dividend_yield__isnull=False, dividend_yield__gte=_min_dy)
        _min_fcfy = _parse_decimal_or_none(q.get("min_fcf_yield"))
        if _min_fcfy is not None:
            qs = qs.filter(fcf_yield__isnull=False, fcf_yield__gte=_min_fcfy)
        if q.get("owner_managed_only", "false").lower() == "true":
            qs = qs.filter(is_owner_managed=True)
        _liq = q.get("min_liquidity_level")
        if _liq:
            threshold = _LIQUIDITY_ORDER.get(_liq, 0)
            allowed = [k for k, v in _LIQUIDITY_ORDER.items() if v >= threshold]
            qs = qs.filter(liquidity_level__in=allowed)
        _mom = q.get("min_momentum_signal")
        if _mom:
            m_threshold = _MOMENTUM_ORDER.get(_mom, 0)
            allowed_m = [k for k, v in _MOMENTUM_ORDER.items() if v >= m_threshold]
            qs = qs.filter(momentum_signal__in=allowed_m)
        for flag in (
            "ma_golden_cross",
            "price_cross_ma25",
            "price_cross_ma75",
            "macd_golden_cross",
            "rsi_rebound",
            "pullback_buy",
        ):
            if q.get(f"{flag}_only", "false").lower() == "true":
                qs = qs.filter(**{flag: True})

        # 軽計算（growth_rate 依存）+ 依存フィルタ
        rows: list[dict[str, Any]] = []
        for snap in qs.iterator(chunk_size=1000):
            calc = apply_growth_rate(snap, growth_rate)
            score = calc["overall_score"]
            if min_overall_score is not None and (score is None or score < min_overall_score):
                continue
            if min_discount is not None:
                dr = calc["discount_rate"]
                if dr is None or Decimal(dr) < min_discount:
                    continue
            rows.append(_row_from_snapshot(snap, calc))

        # ソート（None は末尾）
        def _key(r: dict[str, Any]) -> tuple[int, float]:
            v = r.get(sort_by)
            if v is None:
                return (1, 0.0)
            return (0, float(v))

        rows.sort(key=_key, reverse=order_desc)
        count = len(rows)
        page = rows[offset : offset + limit]
        return Response({"count": count, "results": page, "generated_at": latest.isoformat()})

    def _fallback(
        self,
        request: Request,
        growth_rate: Decimal,
        market_type: str,
        include_inactive: bool,
        limit: int,
        offset: int,
    ) -> Response:
        """スナップショットが無い/古い場合の従来オンザフライ計算。"""
        q = request.query_params
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
            sector=q.get("sector") or None,
            min_discount=_parse_decimal_or_none(q.get("min_discount")),
            include_inactive=include_inactive,
            min_eps_growth_yoy=_parse_decimal_or_none(q.get("min_eps_growth_yoy")),
            min_eps_cagr_3y=_parse_decimal_or_none(q.get("min_eps_cagr_3y")),
            roe_trend_filter=q.get("roe_trend") or None,
            min_roe=_parse_decimal_or_none(q.get("min_roe")),
            max_sl_ratio=_parse_decimal_or_none(q.get("max_sl_ratio")),
            min_dividend_yield=_parse_decimal_or_none(q.get("min_dividend_yield")),
            max_payout_ratio=_parse_decimal_or_none(q.get("max_payout_ratio")),
            min_consecutive_dividend_years=_parse_int_or_none(q.get("min_consecutive_dividend_years")),
            min_progressive_dividend_years=_parse_int_or_none(q.get("min_progressive_dividend_years")),
            min_liquidity_level=q.get("min_liquidity_level") or None,
            min_momentum_signal=q.get("min_momentum_signal") or None,
            owner_managed_only=q.get("owner_managed_only", "false").lower() == "true",
            min_fcf_yield=_parse_decimal_or_none(q.get("min_fcf_yield")),
            ma_golden_cross_only=q.get("ma_golden_cross_only", "false").lower() == "true",
            price_cross_ma25_only=q.get("price_cross_ma25_only", "false").lower() == "true",
            price_cross_ma75_only=q.get("price_cross_ma75_only", "false").lower() == "true",
            macd_golden_cross_only=q.get("macd_golden_cross_only", "false").lower() == "true",
            rsi_rebound_only=q.get("rsi_rebound_only", "false").lower() == "true",
            pullback_buy_only=q.get("pullback_buy_only", "false").lower() == "true",
        )
        rows = [_row_from_result(r) for r in results]
        count = len(rows)
        page = rows[offset : offset + limit]
        return Response({"count": count, "results": page, "generated_at": None})


class ScreeningSectorsView(APIView):
    """GET /api/stocks/screening/sectors/ — スナップショット上のセクター一覧（フィルタUI用）"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        market_type = request.query_params.get("market_type", "JP")
        sectors = list(
            ScreeningSnapshot.objects.filter(market_type=market_type, is_active=True)
            .exclude(sector="")
            .values_list("sector", flat=True)
            .distinct()
            .order_by("sector")
        )
        return Response(sectors)


def _s(v: object) -> str | None:
    return str(v) if v is not None else None


def _row_from_snapshot(snap: ScreeningSnapshot, calc: dict[str, Any]) -> dict[str, Any]:
    """スナップショット行 + 軽計算値 → フロントの ScreeningResult 形の dict。"""
    m = snap.metrics or {}
    return {
        "code": snap.code,
        "name": snap.name,
        "sector": snap.sector,
        "latest_price": m.get("latest_price"),
        "latest_price_date": None,
        "bps": m.get("bps"),
        "eps": m.get("eps"),
        "roe": _s(snap.roe),
        "fair_pbr": calc["fair_pbr"],
        "fair_value": calc["fair_value"],
        "discount_rate": calc["discount_rate"],
        "evaluation_zone": calc["evaluation_zone"],
        "current_pbr": calc["current_pbr"],
        "implied_growth_rate": calc["implied_growth_rate"],
        "growth_rate_label": calc["growth_rate_label"],
        "overall_score": calc["overall_score"],
        "company_forecast_growth_rate": m.get("company_forecast_growth_rate"),
        "is_active": snap.is_active,
        "not_calculable_reason": m.get("not_calculable_reason"),
        "is_manual_financial": m.get("is_manual_financial", False),
        "eps_growth_yoy": m.get("eps_growth_yoy"),
        "eps_cagr_3y": m.get("eps_cagr_3y"),
        "roe_trend": snap.roe_trend,
        "revenue_growth_yoy": m.get("revenue_growth_yoy"),
        "op_income_growth_yoy": m.get("op_income_growth_yoy"),
        "sl_ratio": _s(snap.sl_ratio),
        "long_balance": m.get("long_balance"),
        "short_balance": m.get("short_balance"),
        "long_balance_change": None,
        "long_balance_change_pct": m.get("long_balance_change_pct"),
        "long_balance_trend": m.get("long_balance_trend"),
        "price_position_52w": m.get("price_position_52w"),
        "near_52w_high": None,
        "distance_from_52w_high": m.get("distance_from_52w_high"),
        "volume_ratio_20d": m.get("volume_ratio_20d"),
        "ma_25_deviation": m.get("ma_25_deviation"),
        "momentum_signal": snap.momentum_signal,
        "avg_turnover_20d": m.get("avg_turnover_20d"),
        "liquidity_level": snap.liquidity_level,
        "dividend_yield": _s(snap.dividend_yield),
        "payout_ratio": m.get("payout_ratio"),
        "consecutive_dividend_years": m.get("consecutive_dividend_years"),
        "progressive_dividend_years": m.get("progressive_dividend_years"),
        "dividend_score": m.get("dividend_score"),
        "fcf": m.get("fcf"),
        "fcf_yield": _s(snap.fcf_yield),
        "fcf_margin": m.get("fcf_margin"),
        "fcf_score": m.get("fcf_score"),
        "is_owner_managed": snap.is_owner_managed,
        "owner_ratio": m.get("owner_ratio"),
        "owner_match_type": m.get("owner_match_type"),
    }


def _row_from_result(r: ScreeningResult) -> dict[str, Any]:
    """オンザフライ ScreeningResult → 同形の dict（フォールバック用）。overall_score は含めない。"""
    return {
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
        "overall_score": None,
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


def _parse_decimal(value: str | None, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(value)
    except InvalidOperation:
        return default


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
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
