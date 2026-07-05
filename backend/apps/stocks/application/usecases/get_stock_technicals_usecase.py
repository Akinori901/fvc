"""銘柄テクニカル指標取得 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.stocks.domain.stock_technical_indicators import (
    StockTechnicalIndicators,
    build_indicators,
)

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import PriceRepository, StockRepository


# 期間ごとの末尾トリム日数（営業日ベース）
_PERIOD_TRIM = {
    "1m": 22,
    "3m": 66,
    "6m": 132,
    "1y": 252,
    "all": None,  # トリムせず全期間
}

# 200日MAの warmup を含む取得日数（カレンダー日数ではなく営業日 limit）
_FETCH_LIMIT = 300


class GetStockTechnicalsUseCase:
    """銘柄テクニカル指標を計算して返す。"""

    def __init__(self, stock_repo: StockRepository, price_repo: PriceRepository) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo

    def execute(self, code: str, period: str = "1y") -> StockTechnicalIndicators | None:
        """銘柄コードと期間からテクニカル指標を計算する。

        Args:
            code: 銘柄コード
            period: '1m' | '3m' | '6m' | '1y' | 'all'

        Returns:
            StockTechnicalIndicators または None（銘柄が見つからない場合）
        """
        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            return None

        # 降順で 300 件取得（200日MA + warmup 50日を確保）
        prices_desc = self._price_repo.find_by_stock_id(stock.id, limit=_FETCH_LIMIT)
        if not prices_desc:
            return StockTechnicalIndicators()

        indicators = build_indicators(prices_desc)

        # series を period に応じてトリム
        trim = _PERIOD_TRIM.get(period, _PERIOD_TRIM["1y"])
        if trim is not None and len(indicators.series) > trim:
            indicators.series = indicators.series[-trim:]

        return indicators
