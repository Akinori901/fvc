"""財務データ同期サービス（バルク取得対応）。"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.entities import StockEntity
    from apps.stocks.domain.repositories import FinancialRepository, MarketDataProvider, StockRepository

logger = logging.getLogger(__name__)


class FinancialSyncService:
    """外部プロバイダーから取得した財務データを同期する。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        fallback_provider: MarketDataProvider | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._fallback_provider = fallback_provider

    def sync(
        self,
        provider: MarketDataProvider,
        market_type: str,
        codes: list[str] | None = None,
        fiscal_year: int | None = None,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """財務データを同期し (成功件数, エラー件数, エラー詳細) を返す。

        財務データは銘柄ごとに get_fin_summary を呼ぶ。
        コード未指定の場合は株価データが存在する銘柄（watchlist/active銘柄）のみ対象。
        """
        return self._sync_per_stock(provider, market_type, codes, fiscal_year)

    def _sync_bulk(
        self,
        provider: MarketDataProvider,
        market_type: str,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """全銘柄の財務データを一括取得。"""
        from apps.stocks.domain.entities import FinancialEntity

        stocks = self._stock_repo.find_by_market_type(market_type)
        if not stocks:
            return 0, 0, []

        code_to_stock = {s.code: s for s in stocks}

        to_date = date.today()
        from_date = to_date - timedelta(days=60)  # 60日以内の開示データを一括取得

        try:
            all_financials = provider.fetch_all_financials(from_date, to_date)
        except Exception as e:
            logger.error("一括財務データ取得に失敗: %s", e)
            return 0, 1, [{"code": "*", "error": str(e)}]

        if not all_financials:
            logger.warning("一括取得結果が空")
            return 0, 0, []

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []
        seen_codes: set[str] = set()

        for data in all_financials:
            stock = code_to_stock.get(data.code)
            if not stock or stock.id is None:
                continue

            try:
                entity = FinancialEntity(
                    stock_id=stock.id,
                    fiscal_year=data.fiscal_year,
                    bps=data.bps,
                    eps=data.eps,
                    roe=data.roe,
                    net_assets=data.net_assets,
                    total_shares=data.total_shares,
                    revenue=data.revenue,
                    operating_income=data.operating_income,
                    eps_forecast=data.eps_forecast,
                    period_end_date=data.period_end_date,
                )
                self._financial_repo.save(entity)
                seen_codes.add(data.code)
            except Exception as e:
                error_count += 1
                errors.append({"code": data.code, "error": str(e)})

        success_count = len(seen_codes)
        logger.info("財務データ一括同期完了: 成功=%d銘柄, エラー=%d銘柄", success_count, error_count)
        return success_count, error_count, errors

    def _sync_per_stock(
        self,
        provider: MarketDataProvider,
        market_type: str,
        codes: list[str] | None = None,
        fiscal_year: int | None = None,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """銘柄ごとに財務データを取得（従来方式）。"""
        import time

        from apps.stocks.domain.entities import FinancialEntity

        stocks = self._get_target_stocks(market_type, codes)
        if not stocks:
            return 0, 0, []

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []
        # コード指定なし（全銘柄）の場合はレートリミット対策で間隔を空ける
        sleep_interval = 0.0 if codes else 0.5

        for stock in stocks:
            try:
                if sleep_interval:
                    time.sleep(sleep_interval)
                financials = provider.fetch_financials(stock.code, fiscal_year=fiscal_year)
                if not financials and self._fallback_provider:
                    logger.info("銘柄 %s: プロバイダーで財務データなし、フォールバックで再試行", stock.code)
                    financials = self._fallback_provider.fetch_financials(stock.code, fiscal_year=fiscal_year)
                if not financials:
                    continue

                entities = []
                for data in financials:
                    assert stock.id is not None
                    entities.append(
                        FinancialEntity(
                            stock_id=stock.id,
                            fiscal_year=data.fiscal_year,
                            bps=data.bps,
                            eps=data.eps,
                            roe=data.roe,
                            net_assets=data.net_assets,
                            total_shares=data.total_shares,
                            revenue=data.revenue,
                            operating_income=data.operating_income,
                            eps_forecast=data.eps_forecast,
                            period_end_date=data.period_end_date,
                            operating_cash_flow=data.operating_cash_flow,
                            free_cash_flow=data.free_cash_flow,
                        )
                    )

                self._financial_repo.bulk_save(entities)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"code": stock.code, "error": str(e)})
                logger.warning("銘柄 %s の財務データ同期に失敗: %s", stock.code, e)

        logger.info("財務データ同期完了: 成功=%d銘柄, エラー=%d銘柄", success_count, error_count)
        return success_count, error_count, errors

    def _get_target_stocks(self, market_type: str, codes: list[str] | None) -> list[StockEntity]:
        """同期対象の銘柄リストを取得。"""
        if codes:
            stocks = []
            for code in codes:
                stock = self._stock_repo.find_by_code(code)
                if stock:
                    stocks.append(stock)
                else:
                    logger.warning("銘柄が見つかりません: %s", code)
            return stocks
        return self._stock_repo.find_by_market_type(market_type)
