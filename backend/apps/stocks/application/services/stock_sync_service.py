"""銘柄マスタ同期サービス。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import MarketDataProvider, StockRepository

logger = logging.getLogger(__name__)


class StockSyncService:
    """外部プロバイダーから取得した銘柄一覧でマスタを upsert する。"""

    def __init__(self, stock_repo: StockRepository) -> None:
        self._stock_repo = stock_repo

    def sync(self, provider: MarketDataProvider) -> tuple[int, int, list[dict[str, str]]]:
        """銘柄一覧を同期し (成功件数, エラー件数, エラー詳細) を返す。"""
        from apps.stocks.domain.entities import StockEntity

        market_data = provider.fetch_stock_list()
        if not market_data:
            logger.warning("プロバイダー %s から銘柄データが取得できませんでした", provider.get_provider_name())
            return 0, 0, []

        # 市場タイプ別にアクティブコードを収集（廃止銘柄マーク用）
        market_type_to_codes: dict[str, set[str]] = {}
        for data in market_data:
            market_type_to_codes.setdefault(data.market_type, set()).add(data.code)

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []

        for data in market_data:
            try:
                entity = StockEntity(
                    code=data.code,
                    name=data.name,
                    market=data.market,
                    market_type=data.market_type,
                    instrument_type=data.instrument_type,
                    sector=data.sector,
                    is_active=True,
                )
                self._stock_repo.upsert(entity)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"code": data.code, "error": str(e)})
                logger.warning("銘柄 %s の同期に失敗: %s", data.code, e)

        # 取得リストにない銘柄を上場廃止としてマーク
        for market_type, active_codes in market_type_to_codes.items():
            deactivated = self._stock_repo.deactivate_missing(market_type, active_codes)
            if deactivated > 0:
                logger.info("市場 %s: %d 銘柄を上場廃止にマーク", market_type, deactivated)

        logger.info("銘柄同期完了: 成功=%d, エラー=%d", success_count, error_count)
        return success_count, error_count, errors
