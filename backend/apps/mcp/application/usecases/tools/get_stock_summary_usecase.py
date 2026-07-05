"""銘柄サマリ取得ツール UseCase。

既存 ScreeningUseCase の単一銘柄モード（code 指定）を呼び、ScreeningResult を MCP 用の dict に整形して返す。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase

# Gordon Growth model の前提成長率（年率 2%）— 既存 ScreeningView と揃える
_DEFAULT_GROWTH_RATE = Decimal("0.02")


class GetStockSummaryToolUseCase:
    """単一銘柄の MCP サマリを返す。

    依存は ScreeningUseCase を直接受け取る形（既存 Web 画面と同じファクトリ）。
    """

    def __init__(self, screening_usecase: ScreeningUseCase) -> None:
        self._screening_usecase = screening_usecase

    def execute(self, *, code: str) -> dict[str, Any]:
        results = self._screening_usecase.execute(
            growth_rate=_DEFAULT_GROWTH_RATE,
            code=code,
            include_inactive=True,
        )
        if not results:
            raise ValueError(f"銘柄が見つかりません: {code}")

        r = results[0]
        return {
            "code": r.code,
            "name": r.name,
            "sector": r.sector,
            "is_active": r.is_active,
            "latest_price": _decimal_or_none(r.latest_price),
            "latest_price_date": r.latest_price_date,
            "bps": _decimal_or_none(r.bps),
            "eps": _decimal_or_none(r.eps),
            "roe": _decimal_or_none(r.roe),
            "current_pbr": _decimal_or_none(r.current_pbr),
            "fair_pbr": _decimal_or_none(r.fair_pbr),
            "fair_value": _decimal_or_none(r.fair_value),
            "discount_rate": _decimal_or_none(r.discount_rate),
            "evaluation_zone": r.evaluation_zone,
            "implied_growth_rate": _decimal_or_none(r.implied_growth_rate),
            "growth_rate_label": r.growth_rate_label,
            "eps_growth_yoy": _decimal_or_none(r.eps_growth_yoy),
            "eps_cagr_3y": _decimal_or_none(r.eps_cagr_3y),
            "roe_trend": r.roe_trend,
            "high_52w": None,  # ScreeningResult に直接の field は無し（price_position_52w で表現）
            "low_52w": None,
            "price_position_52w": _decimal_or_none(r.price_position_52w),
            "near_52w_high": r.near_52w_high,
            "distance_from_52w_high": _decimal_or_none(r.distance_from_52w_high),
            "momentum_signal": r.momentum_signal,
            "dividend_yield": _decimal_or_none(r.dividend_yield),
            "payout_ratio": _decimal_or_none(r.payout_ratio),
            "consecutive_dividend_years": r.consecutive_dividend_years,
            "progressive_dividend_years": r.progressive_dividend_years,
            "liquidity_level": r.liquidity_level,
            "not_calculable_reason": r.not_calculable_reason,
            "growth_rate_assumed": str(_DEFAULT_GROWTH_RATE),
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
