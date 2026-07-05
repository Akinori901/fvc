"""買い候補銘柄抽出ツール UseCase。

ScreeningUseCase の全件モードを呼び、ツール層で追加フィルタ（PBR 倍率上限・評価ゾーン制限・
除外コード・件数制限）を適用して買い候補銘柄を返す。

ScreeningUseCase 自体に無いフィルタはここで post-filter する設計とし、
ScreeningUseCase の責務を肥大化させない。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import (
        ScreeningResult,
        ScreeningUseCase,
    )


_DEFAULT_GROWTH_RATE = Decimal("0.02")
_DEFAULT_INCLUDE_ZONES = ("very_cheap", "cheap", "fair")
_DEFAULT_MIN_MOMENTUM = "neutral"
_DEFAULT_LIMIT = 20


class GetScreeningCandidatesToolUseCase:
    """買い候補銘柄を抽出する。"""

    def __init__(self, screening_usecase: ScreeningUseCase) -> None:
        self._screening_usecase = screening_usecase

    def execute(
        self,
        *,
        growth_rate: Decimal | None = None,
        max_pbr_ratio: Decimal | None = None,
        min_roe: Decimal | None = None,
        include_zones: list[str] | None = None,
        min_momentum_signal: str | None = None,
        exclude_codes: list[str] | None = None,
        limit: int = _DEFAULT_LIMIT,
        market_type: str = "JP",
    ) -> dict[str, Any]:
        results = self._screening_usecase.execute(
            growth_rate=growth_rate or _DEFAULT_GROWTH_RATE,
            market_type=market_type,
            min_roe=min_roe,
            min_momentum_signal=min_momentum_signal or _DEFAULT_MIN_MOMENTUM,
        )

        zones = set(include_zones or _DEFAULT_INCLUDE_ZONES)
        excluded = set(exclude_codes or [])

        filtered: list[ScreeningResult] = []
        for r in results:
            if r.fair_value is None or r.evaluation_zone is None:
                continue
            if r.evaluation_zone not in zones:
                continue
            if r.code in excluded:
                continue
            if _is_excluded_by_pbr_ratio(r, max_pbr_ratio):
                continue
            filtered.append(r)
            if len(filtered) >= limit:
                break

        return {
            "count": len(filtered),
            "candidates": [_to_dto(r) for r in filtered],
            "filters_applied": {
                "growth_rate": str(growth_rate or _DEFAULT_GROWTH_RATE),
                "max_pbr_ratio": _decimal_or_none(max_pbr_ratio),
                "min_roe": _decimal_or_none(min_roe),
                "include_zones": sorted(zones),
                "min_momentum_signal": min_momentum_signal or _DEFAULT_MIN_MOMENTUM,
                "exclude_codes": sorted(excluded),
                "limit": limit,
            },
        }


def _to_dto(r: ScreeningResult) -> dict[str, Any]:
    return {
        "code": r.code,
        "name": r.name,
        "sector": r.sector,
        "latest_price": _decimal_or_none(r.latest_price),
        "current_pbr": _decimal_or_none(r.current_pbr),
        "fair_pbr": _decimal_or_none(r.fair_pbr),
        "fair_value": _decimal_or_none(r.fair_value),
        "discount_rate": _decimal_or_none(r.discount_rate),
        "evaluation_zone": r.evaluation_zone,
        "roe": _decimal_or_none(r.roe),
        "roe_trend": r.roe_trend,
        "momentum_signal": r.momentum_signal,
        "dividend_yield": _decimal_or_none(r.dividend_yield),
        "liquidity_level": r.liquidity_level,
    }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _is_excluded_by_pbr_ratio(r: ScreeningResult, max_pbr_ratio: Decimal | None) -> bool:
    """current_pbr が fair_pbr × max_pbr_ratio を超えていれば除外。"""
    if max_pbr_ratio is None:
        return False
    if r.current_pbr is None or r.fair_pbr is None or r.fair_pbr <= 0:
        return False
    return r.current_pbr > r.fair_pbr * max_pbr_ratio
