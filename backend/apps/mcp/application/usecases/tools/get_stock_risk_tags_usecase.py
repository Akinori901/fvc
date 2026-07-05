"""銘柄リスクタグ取得ツール UseCase。

ScreeningUseCase で対象銘柄を評価し、stock_tags.compute_risk_tags で
リスクタグのリストを算出して返す。
"""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ....domain.stock_tags import compute_risk_tags

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase


_DEFAULT_GROWTH_RATE = Decimal("0.02")


class GetStockRiskTagsToolUseCase:
    """銘柄のリスクタグ（注意事項）を返す。"""

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

        result = results[0]
        tags = compute_risk_tags(result)

        return {
            "code": result.code,
            "name": result.name,
            "as_of": result.latest_price_date,
            "risk_tags": [asdict(t) for t in tags],
        }
