"""市場データ同期ユースケース。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from datetime import date

    from apps.stocks.application.services.dividend_sync_service import DividendSyncService
    from apps.stocks.application.services.financial_sync_service import FinancialSyncService
    from apps.stocks.application.services.market_data_provider_resolver import MarketDataProviderResolver
    from apps.stocks.application.services.price_sync_service import PriceSyncService
    from apps.stocks.application.services.stock_sync_service import StockSyncService
    from apps.stocks.domain.entities import SyncLogEntity
    from apps.stocks.domain.repositories import SyncLogRepository

logger = logging.getLogger(__name__)


class SyncMarketDataUseCase:
    """市場データ同期のオーケストレーション + ログ記録。"""

    def __init__(
        self,
        provider_resolver: MarketDataProviderResolver,
        stock_sync_service: StockSyncService,
        financial_sync_service: FinancialSyncService,
        price_sync_service: PriceSyncService,
        sync_log_repo: SyncLogRepository,
        dividend_sync_service: DividendSyncService | None = None,
    ) -> None:
        self._provider_resolver = provider_resolver
        self._stock_sync_service = stock_sync_service
        self._financial_sync_service = financial_sync_service
        self._price_sync_service = price_sync_service
        self._sync_log_repo = sync_log_repo
        self._dividend_sync_service = dividend_sync_service

    def sync_stocks(self, market_type: str = "JP") -> SyncLogEntity:
        """銘柄マスタを同期。"""
        provider = self._provider_resolver.resolve(market_type)
        log = self._create_log("stocks", provider.get_provider_name(), market_type)

        success, errors_count, errors = self._stock_sync_service.sync(provider)

        return self._finish_log(log, success + errors_count, success, errors_count, errors)

    def sync_financials(
        self,
        market_type: str = "JP",
        codes: list[str] | None = None,
        fiscal_year: int | None = None,
    ) -> SyncLogEntity:
        """財務データを同期。"""
        provider = self._provider_resolver.resolve(market_type)
        log = self._create_log("financials", provider.get_provider_name(), market_type)

        success, errors_count, errors = self._financial_sync_service.sync(
            provider, market_type, codes=codes, fiscal_year=fiscal_year
        )

        return self._finish_log(log, success + errors_count, success, errors_count, errors)

    def sync_prices(
        self,
        market_type: str = "JP",
        codes: list[str] | None = None,
        from_date: date | None = None,
        force: bool = False,
    ) -> SyncLogEntity:
        """株価データを同期。"""
        provider = self._provider_resolver.resolve(market_type)
        log = self._create_log("prices", provider.get_provider_name(), market_type)

        success, errors_count, errors = self._price_sync_service.sync(
            provider, market_type, codes=codes, from_date=from_date, force=force
        )

        return self._finish_log(log, success + errors_count, success, errors_count, errors)

    def sync_dividends(
        self,
        market_type: str = "JP",
        codes: list[str] | None = None,
        instrument_type: str | None = None,
    ) -> SyncLogEntity:
        """配当・分配金データを同期。instrument_type で対象種別を指定可能。"""
        if self._dividend_sync_service is None:
            raise RuntimeError("DividendSyncService が設定されていません")
        # 配当データは yfinance フォールバックを使うため dividend_provider を解決
        provider = self._provider_resolver.resolve_dividend(market_type)
        log = self._create_log("dividends", provider.get_provider_name(), market_type)

        success, errors_count, errors = self._dividend_sync_service.sync(
            provider, market_type, codes=codes, instrument_type=instrument_type
        )

        return self._finish_log(log, success + errors_count, success, errors_count, errors)

    def sync_all(self, market_type: str = "JP") -> list[SyncLogEntity]:
        """全データを同期（各同期は独立して実行、部分成功を許容）。"""
        results: list[SyncLogEntity] = []

        logger.info("=== 全データ同期開始 (market=%s) ===", market_type)

        try:
            results.append(self.sync_stocks(market_type))
        except Exception:
            logger.exception("銘柄同期中にエラー")

        try:
            results.append(self.sync_financials(market_type))
        except Exception:
            logger.exception("財務データ同期中にエラー")

        try:
            results.append(self.sync_prices(market_type))
        except Exception:
            logger.exception("株価同期中にエラー")

        if self._dividend_sync_service is not None:
            try:
                results.append(self.sync_dividends(market_type))
            except Exception:
                logger.exception("配当データ同期中にエラー")

        logger.info("=== 全データ同期完了 ===")
        return results

    # ------------------------------------------------------------------
    # ログヘルパー
    # ------------------------------------------------------------------

    def _create_log(self, sync_type: str, provider: str, market: str) -> SyncLogEntity:
        from apps.stocks.domain.entities import SyncLogEntity

        log = SyncLogEntity(
            sync_type=sync_type,
            provider=provider,
            market=market,
            status="running",
            started_at=timezone.now(),
        )
        return self._sync_log_repo.save(log)

    def _finish_log(
        self,
        log: SyncLogEntity,
        total: int,
        success: int,
        error_count: int,
        errors: list[dict[str, str]],
    ) -> SyncLogEntity:
        log.finished_at = timezone.now()
        log.total_count = total
        log.success_count = success
        log.error_count = error_count
        log.error_details = errors
        log.status = "success" if error_count == 0 else ("partial" if success > 0 else "failed")
        return self._sync_log_repo.save(log)
