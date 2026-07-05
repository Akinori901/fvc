"""銘柄機会タグ取得ツール UseCase。

ScreeningUseCase で対象銘柄を評価 + GetStockTechnicalsUseCase で RSI を取得し、
stock_tags.compute_opportunity_tags で機会タグのリストを算出して返す。
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ....domain.stock_tags import compute_opportunity_tags

if TYPE_CHECKING:
    from apps.stocks.application.usecases.get_stock_technicals_usecase import (
        GetStockTechnicalsUseCase,
    )
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase


_DEFAULT_GROWTH_RATE = Decimal("0.02")
_TECHNICALS_PERIOD = "3m"


class GetStockOpportunityTagsToolUseCase:
    """銘柄の機会タグ（買いシグナル候補）を返す。"""

    def __init__(
        self,
        screening_usecase: ScreeningUseCase,
        technicals_usecase: GetStockTechnicalsUseCase,
    ) -> None:
        self._screening_usecase = screening_usecase
        self._technicals_usecase = technicals_usecase

    def execute(self, *, code: str) -> dict[str, Any]:
        results = self._screening_usecase.execute(
            growth_rate=_DEFAULT_GROWTH_RATE,
            code=code,
            include_inactive=True,
        )
        if not results:
            raise ValueError(f"銘柄が見つかりません: {code}")

        result = results[0]
        rsi_14 = self._fetch_rsi_14(code)
        tags = compute_opportunity_tags(result, rsi_14=rsi_14)

        return {
            "code": result.code,
            "name": result.name,
            "as_of": result.latest_price_date,
            "rsi_14": str(rsi_14) if rsi_14 is not None else None,
            "opportunity_tags": [asdict(t) for t in tags],
        }

    def _fetch_rsi_14(self, code: str) -> Decimal | None:
        """RSI 14 を取得。テクニカル取得失敗時は None（タグ判定で除外）。"""
        try:
            indicators = self._technicals_usecase.execute(code, period=_TECHNICALS_PERIOD)
        except Exception:  # noqa: BLE001
            return None
        if indicators is None or indicators.latest is None:
            return None
        return indicators.latest.rsi_14
