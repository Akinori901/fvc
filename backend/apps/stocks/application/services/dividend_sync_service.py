"""配当・分配金同期サービス。ETF・REITの分配金データを同期する。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.entities import StockEntity
    from apps.stocks.domain.repositories import DividendRepository, MarketDataProvider, StockRepository

logger = logging.getLogger(__name__)


class DividendSyncService:
    """外部プロバイダーから配当・分配金データを同期する。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        dividend_repo: DividendRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._dividend_repo = dividend_repo

    def sync(
        self,
        provider: MarketDataProvider,
        market_type: str = "JP",
        codes: list[str] | None = None,
        instrument_type: str | None = None,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """配当・分配金データを同期し (成功件数, エラー件数, エラー詳細) を返す。

        instrument_type で "etf" または "reit" に絞り込み可能。
        None の場合は両方を対象にする。
        """
        import time

        from apps.stocks.domain.entities import DividendEntity

        stocks = self._get_target_stocks(market_type, codes, instrument_type)
        if not stocks:
            return 0, 0, []

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []
        # コード未指定（全件）の場合はレートリミット対策で間隔を空ける
        sleep_interval = 0.0 if codes else 0.5

        for stock in stocks:
            try:
                if sleep_interval:
                    time.sleep(sleep_interval)
                dividends = provider.fetch_dividends(stock.code)
                if not dividends:
                    continue

                assert stock.id is not None
                entities = [
                    DividendEntity(
                        stock_id=stock.id,
                        ex_dividend_date=d.ex_dividend_date,
                        dividends_per_share=d.dividends_per_share,
                        record_date=d.record_date,
                        payable_date=d.payable_date,
                        source=provider.get_provider_name(),
                    )
                    for d in dividends
                ]
                self._dividend_repo.bulk_save(entities)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"code": stock.code, "error": str(e)})
                logger.warning("銘柄 %s の配当データ同期に失敗: %s", stock.code, e)

        logger.info(
            "配当データ同期完了: 成功=%d銘柄, エラー=%d銘柄 (instrument_type=%s)",
            success_count,
            error_count,
            instrument_type or "all",
        )
        return success_count, error_count, errors

    def _get_target_stocks(
        self,
        market_type: str,
        codes: list[str] | None,
        instrument_type: str | None,
    ) -> list[StockEntity]:
        """同期対象の銘柄リストを取得。ETF・REITのみを対象にする。"""
        if codes:
            stocks = []
            for code in codes:
                stock = self._stock_repo.find_by_code(code)
                if stock:
                    stocks.append(stock)
                else:
                    logger.warning("銘柄が見つかりません: %s", code)
            return stocks

        all_stocks = self._stock_repo.find_by_market_type(market_type)
        # instrument_type フィルタ
        if instrument_type:
            return [s for s in all_stocks if s.instrument_type == instrument_type and s.id is not None]
        # 未指定の場合は ETF と REIT のみ対象
        return [s for s in all_stocks if s.instrument_type in ("etf", "reit") and s.id is not None]
