"""株価同期サービス（増分同期 + バルク取得対応）。"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.stocks.domain.entities import StockEntity
    from apps.stocks.domain.repositories import MarketDataProvider, MarketPriceData, PriceRepository, StockRepository

logger = logging.getLogger(__name__)


class PriceSyncService:
    """外部プロバイダーから取得した株価データを増分同期する。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        price_repo: PriceRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo

    def sync(
        self,
        provider: MarketDataProvider,
        market_type: str,
        codes: list[str] | None = None,
        from_date: date | None = None,
        force: bool = False,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """株価データを同期し (成功件数, エラー件数, エラー詳細) を返す。"""
        # バルク取得が可能で、個別銘柄指定・日付指定・強制再取得がない場合は一括取得を使う
        if provider.supports_bulk_fetch() and not codes and not from_date and not force:
            return self._sync_bulk(provider, market_type)
        return self._sync_per_stock(provider, market_type, codes, from_date, force)

    def _sync_bulk(
        self,
        provider: MarketDataProvider,
        market_type: str,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """全銘柄の株価を日付ベースで一括取得。"""
        from apps.stocks.domain.entities import PriceEntity

        stocks = self._stock_repo.find_by_market_type(market_type)
        if not stocks:
            return 0, 0, []

        code_to_stock = {s.code: s for s in stocks}

        # 当日の株価を一括取得（データがなければ最大3営業日前まで遡る）
        all_prices: list[MarketPriceData] = []
        today = date.today()
        target_date = today
        for days_back in range(4):
            candidate = today - timedelta(days=days_back)
            try:
                all_prices = provider.fetch_all_prices(candidate)
                if all_prices:
                    target_date = candidate
                    break
                logger.info("一括株価: %s はデータなし、前日を試行", candidate)
            except Exception as e:
                logger.error("一括株価取得に失敗 (date=%s): %s", candidate, e)

        if not all_prices:
            logger.warning("一括取得結果が空（直近4日分を試行済み）")
            return 0, 0, []

        if target_date < today:
            logger.warning(
                "本日(%s)の株価データが未公開のため、%s のデータで代替。"
                "19:00 以降の同期で当日データが取得される見込みです。",
                today,
                target_date,
            )

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []
        latest_prices: list[tuple[int, Decimal, date]] = []

        for data in all_prices:
            stock = code_to_stock.get(data.code)
            if not stock or stock.id is None:
                continue

            try:
                entity = PriceEntity(
                    stock_id=stock.id,
                    date=data.date.isoformat(),
                    close_price=data.close_price,
                    volume=data.volume,
                    adj_factor=data.adj_factor,
                    is_limit_up=data.is_limit_up,
                    is_limit_down=data.is_limit_down,
                )
                self._price_repo.save(entity)
                latest_prices.append((stock.id, data.close_price, data.date))
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"code": data.code, "error": str(e)})

        # m_stocks.latest_price を一括更新
        if latest_prices:
            self._stock_repo.bulk_update_latest_prices(latest_prices)

        logger.info("株価一括同期完了: 成功=%d銘柄, エラー=%d銘柄", success_count, error_count)
        return success_count, error_count, errors

    def _sync_per_stock(
        self,
        provider: MarketDataProvider,
        market_type: str,
        codes: list[str] | None = None,
        from_date: date | None = None,
        force: bool = False,
    ) -> tuple[int, int, list[dict[str, str]]]:
        """銘柄ごとに株価を取得（従来方式）。"""
        from apps.stocks.domain.entities import PriceEntity

        stocks = self._get_target_stocks(market_type, codes)
        if not stocks:
            return 0, 0, []

        success_count = 0
        error_count = 0
        errors: list[dict[str, str]] = []
        latest_prices: list[tuple[int, Decimal, date]] = []

        for stock in stocks:
            try:
                assert stock.id is not None
                sync_from = self._determine_from_date(stock.id, from_date, force)

                prices = provider.fetch_prices(
                    stock.code,
                    from_date=sync_from,
                    to_date=date.today(),
                )
                if not prices:
                    continue

                entities = []
                for data in prices:
                    entities.append(
                        PriceEntity(
                            stock_id=stock.id,
                            date=data.date.isoformat(),
                            close_price=data.close_price,
                            volume=data.volume,
                            adj_factor=data.adj_factor,
                            is_limit_up=data.is_limit_up,
                            is_limit_down=data.is_limit_down,
                        )
                    )

                self._price_repo.bulk_save(entities)

                # 最新株価を記録
                latest = max(prices, key=lambda p: p.date)
                latest_prices.append((stock.id, latest.close_price, latest.date))

                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({"code": stock.code, "error": str(e)})
                logger.warning("銘柄 %s の株価同期に失敗: %s", stock.code, e)

        # m_stocks.latest_price を一括更新
        if latest_prices:
            self._stock_repo.bulk_update_latest_prices(latest_prices)

        logger.info("株価同期完了: 成功=%d銘柄, エラー=%d銘柄", success_count, error_count)
        return success_count, error_count, errors

    def _determine_from_date(self, stock_id: int, from_date: date | None, force: bool) -> date | None:
        """増分同期の開始日を決定。"""
        if from_date:
            return from_date
        if force:
            return None

        latest_str = self._price_repo.find_latest_date_by_stock_id(stock_id)
        if latest_str:
            latest = date.fromisoformat(latest_str)
            return latest + timedelta(days=1)
        return None

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
