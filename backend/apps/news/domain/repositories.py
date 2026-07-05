"""ニュース機能リポジトリインターフェース。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from .entities import (
        NewsAiAnalysisEntity,
        NewsArticleEntity,
        NewsKeywordEntity,
        NewsStockLinkEntity,
    )


class NewsArticleRepository(ABC):
    """ニュース記事リポジトリ"""

    @abstractmethod
    def find_by_id(self, news_id: int) -> NewsArticleEntity | None: ...

    @abstractmethod
    def find_by_source_article_id(self, source: str, source_article_id: str) -> NewsArticleEntity | None: ...

    @abstractmethod
    def list_articles(
        self,
        *,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        keyword: str | None = None,
        stock_id: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> tuple[list[NewsArticleEntity], int]:
        """フィルタ条件で記事一覧を取得。返り値は (entities, total_count)。"""

    @abstractmethod
    def list_articles_for_stocks(
        self,
        *,
        stock_ids: list[int],
        days: int = 7,
        min_importance: Decimal | None = None,
        limit: int = 20,
    ) -> tuple[list[NewsArticleEntity], int]:
        """複数銘柄に紐づく記事を一括取得（distinct 済み）。

        Args:
            stock_ids: 対象銘柄 ID（空リストなら ([], 0) を返す）
            days: 直近 N 日（published_at が now - days 以降）
            min_importance: importance_score の下限（None なら無条件）
            limit: 最大件数

        Returns: (entities, total_count)
        """

    @abstractmethod
    def save(self, entity: NewsArticleEntity) -> NewsArticleEntity:
        """記事を保存。source + source_article_id が既存なら更新（id を返す）。"""


class NewsStockLinkRepository(ABC):
    """ニュース × 銘柄リンクリポジトリ"""

    @abstractmethod
    def bulk_save(self, entities: list[NewsStockLinkEntity]) -> int: ...

    @abstractmethod
    def find_stock_ids_by_news_id(self, news_id: int) -> list[int]: ...


class NewsAiAnalysisRepository(ABC):
    """ニュース AI 分析結果リポジトリ（Phase 2 で本格利用）"""

    @abstractmethod
    def find_batch_by_news_id(self, news_id: int) -> NewsAiAnalysisEntity | None:
        """バッチ事前分析（user_id IS NULL）を取得。"""

    @abstractmethod
    def save(self, entity: NewsAiAnalysisEntity) -> NewsAiAnalysisEntity: ...


class NewsKeywordRepository(ABC):
    """ニュース検索キーワードリポジトリ（Phase 2 で本格利用）"""

    @abstractmethod
    def find_active_by_category(self, category: str) -> list[NewsKeywordEntity]: ...
