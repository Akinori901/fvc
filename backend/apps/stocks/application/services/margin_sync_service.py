"""信用取引残高データ同期サービス。"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import MarginRepository, MarketDataProvider, StockRepository

logger = logging.getLogger(__name__)


class MarginSyncService:
    """信用取引残高データの同期サービス。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        margin_repo: MarginRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._margin_repo = margin_repo

    def sync(
        self,
        provider: MarketDataProvider,
        market_type: str = "JP",
        codes: list[str] | None = None,
        from_date: date | None = None,
    ) -> tuple[int, int, list[str]]:
        """信用残高を同期する（一括取得方式）。

        Returns:
            (total_stocks, saved_records, error_messages)
        """
        if not provider.supports_margin_fetch():
            logger.warning("プロバイダー %s は信用残高取得に非対応", provider.get_provider_name())
            return 0, 0, []

        stocks = self._stock_repo.find_by_market_type(market_type)
        if codes:
            stocks = [s for s in stocks if s.code in codes]

        stock_map = {s.code: s.id for s in stocks if s.id is not None}

        if from_date is None:
            from_date = date.today() - timedelta(days=90)

        # 全銘柄を一括取得（per-stock ループ → 1回のAPIコールに変更）
        all_data = provider.fetch_all_margin_balance(from_date=from_date, to_date=date.today())

        saved = self._margin_repo.bulk_save(all_data, stock_map)
        logger.info(
            "信用残高同期完了: %d 銘柄, %d 件保存, 0 エラー",
            len(stocks),
            saved,
        )
        return len(stocks), saved, []
