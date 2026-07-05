"""ニュース取り込み（保存）サービス。

外部クライアントから取得した NewsItemDTO を、銘柄マッチ結果と重要度スコアと共に DB に保存する。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...domain.entities import NewsArticleEntity, NewsStockLinkEntity

if TYPE_CHECKING:
    from decimal import Decimal

    from ...domain.repositories import NewsArticleRepository, NewsStockLinkRepository
    from ..dto import MatchedStockDTO, NewsItemDTO

logger = logging.getLogger(__name__)


class NewsSyncService:
    """ニュース記事 + 銘柄リンクの保存責務（単一責任）"""

    def __init__(
        self,
        article_repo: NewsArticleRepository,
        stock_link_repo: NewsStockLinkRepository,
    ) -> None:
        self._article_repo = article_repo
        self._stock_link_repo = stock_link_repo

    def upsert_article_with_links(
        self,
        *,
        item: NewsItemDTO,
        category: str,
        importance_score: Decimal,
        matched_stocks: list[MatchedStockDTO],
    ) -> tuple[NewsArticleEntity, int, bool]:
        """記事 upsert + 銘柄リンク bulk_save。

        Returns:
            (saved_entity, links_created, is_new)
        """
        existing = self._article_repo.find_by_source_article_id(item.source, item.source_article_id)
        is_new = existing is None

        entity = NewsArticleEntity(
            id=existing.id if existing else None,
            source=item.source,
            source_article_id=item.source_article_id,
            category=category,
            title=item.title,
            url=item.url,
            summary=_truncate(item.summary, 500),
            publisher=item.publisher,
            language=item.language,
            published_at=item.published_at,
            importance_score=importance_score,
        )
        saved = self._article_repo.save(entity)
        if saved.id is None:
            raise RuntimeError("NewsArticle save returned without id")

        links_created = 0
        if matched_stocks:
            from decimal import Decimal

            link_entities = [
                NewsStockLinkEntity(
                    news_id=saved.id,
                    stock_id=m.stock_id,
                    relevance_score=Decimal(str(m.relevance_score)),
                    matched_by=m.matched_by,
                )
                for m in matched_stocks
            ]
            links_created = self._stock_link_repo.bulk_save(link_entities)

        return saved, links_created, is_new


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars]
