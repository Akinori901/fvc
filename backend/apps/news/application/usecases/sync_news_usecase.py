"""ニュース取り込みユースケース。

カテゴリ別に外部ソースから取得し、銘柄マッチ・重要度算出・DB保存をオーケストレーションする。
Phase 1 では category="stock" のみ対応。
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from django.db import transaction

from ...domain.entities import CATEGORY_STOCK, VALID_CATEGORIES
from ...domain.exceptions import NewsSourceError
from ..dto import SyncNewsResultDTO

if TYPE_CHECKING:
    from apps.stocks.domain.entities import StockEntity
    from apps.stocks.domain.repositories import StockRepository

    from ..services.google_news_rss_client_service import GoogleNewsRssClientService
    from ..services.news_importance_service import NewsImportanceService
    from ..services.news_matching_service import NewsMatchingService
    from ..services.news_sync_service import NewsSyncService

logger = logging.getLogger(__name__)

# Google News RSS への連続リクエストでブロックされるのを防ぐ
_RSS_REQUEST_INTERVAL_SEC = 0.5


class SyncNewsUseCase:
    """ニュース取り込みオーケストレーション"""

    def __init__(
        self,
        google_news_client: GoogleNewsRssClientService,
        matching_service: NewsMatchingService,
        importance_service: NewsImportanceService,
        sync_service: NewsSyncService,
        stock_repo: StockRepository,
    ) -> None:
        self._google_news_client = google_news_client
        self._matching_service = matching_service
        self._importance_service = importance_service
        self._sync_service = sync_service
        self._stock_repo = stock_repo

    def execute(
        self,
        *,
        category: str,
        code: str | None = None,
        limit_per_stock: int = 20,
        max_stocks: int | None = None,
    ) -> SyncNewsResultDTO:
        """カテゴリ別に取り込み。

        Args:
            category: "stock" のみ Phase 1 で対応
            code: 特定銘柄のみを対象（動作確認用）
            limit_per_stock: 1銘柄あたりの取得件数上限
            max_stocks: 全銘柄取り込み時の上限件数（デバッグ用）
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(f"未知のカテゴリ: {category}")
        if category != CATEGORY_STOCK:
            # Phase 1 では stock のみ対応
            raise NotImplementedError(f"カテゴリ '{category}' は Phase 2 で実装予定です")

        result = SyncNewsResultDTO()

        target_stocks = self._resolve_target_stocks(code=code, max_stocks=max_stocks)
        if not target_stocks:
            logger.info("sync_news[stock]: 対象銘柄なし")
            return result

        # マッチ判定用に全銘柄リストを一度だけ取得
        all_active_stocks = self._stock_repo.find_by_market_type("JP", active_only=True)

        for idx, stock in enumerate(target_stocks):
            try:
                self._sync_one_stock(
                    stock=stock,
                    all_active_stocks=all_active_stocks,
                    limit_per_stock=limit_per_stock,
                    result=result,
                )
            except NewsSourceError as exc:
                msg = f"{stock.code} {stock.name}: {exc}"
                logger.warning("sync_news source error: %s", msg)
                result.errors.append(msg)
            except Exception as exc:  # noqa: BLE001
                msg = f"{stock.code} {stock.name}: 想定外エラー {exc!r}"
                logger.exception("sync_news unexpected error for %s", stock.code)
                result.errors.append(msg)

            # 連続リクエスト抑制
            if idx < len(target_stocks) - 1:
                time.sleep(_RSS_REQUEST_INTERVAL_SEC)

        logger.info(
            "sync_news[stock] 完了: fetched=%d saved=%d links=%d skipped=%d errors=%d",
            result.fetched,
            result.saved,
            result.matched_links,
            result.skipped_irrelevant,
            len(result.errors),
        )
        return result

    def _resolve_target_stocks(self, *, code: str | None, max_stocks: int | None) -> list[StockEntity]:
        if code:
            stock = self._stock_repo.find_by_code(code)
            if stock is None:
                raise ValueError(f"銘柄が見つかりません: {code}")
            return [stock]

        stocks = self._stock_repo.find_by_market_type("JP", active_only=True)
        if max_stocks is not None:
            stocks = stocks[:max_stocks]
        return stocks

    def _sync_one_stock(
        self,
        *,
        stock: StockEntity,
        all_active_stocks: list[StockEntity],
        limit_per_stock: int,
        result: SyncNewsResultDTO,
    ) -> None:
        with transaction.atomic():
            self._sync_one_stock_body(
                stock=stock,
                all_active_stocks=all_active_stocks,
                limit_per_stock=limit_per_stock,
                result=result,
            )

    def _sync_one_stock_body(
        self,
        *,
        stock: StockEntity,
        all_active_stocks: list[StockEntity],
        limit_per_stock: int,
        result: SyncNewsResultDTO,
    ) -> None:
        query = _build_query(stock.name)
        items = self._google_news_client.fetch(query, limit=limit_per_stock)
        result.fetched += len(items)

        for item in items:
            text = f"{item.title} {item.summary}"
            matched = self._matching_service.match(text=text, candidate_stocks=all_active_stocks)

            # 取り込み対象銘柄自体がマッチに含まれていない場合は誤検知としてスキップ
            if not any(m.stock_id == stock.id for m in matched):
                result.skipped_irrelevant += 1
                continue

            importance = self._importance_service.compute(
                item=item,
                category=CATEGORY_STOCK,
                matched_stocks=matched,
            )
            _saved, links_created, is_new = self._sync_service.upsert_article_with_links(
                item=item,
                category=CATEGORY_STOCK,
                importance_score=importance,
                matched_stocks=matched,
            )
            if is_new:
                result.saved += 1
            result.matched_links += links_created


def _build_query(stock_name: str) -> str:
    """銘柄名から Google News RSS 用の検索クエリを構築。"""
    return f'"{stock_name}" 株価 OR 決算 OR 業績'
