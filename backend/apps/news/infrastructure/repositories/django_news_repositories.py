"""ニュース機能リポジトリ Django ORM 実装。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import Q

from ...domain.entities import (
    NewsAiAnalysisEntity,
    NewsArticleEntity,
    NewsKeywordEntity,
    NewsStockLinkEntity,
)
from ...domain.repositories import (
    NewsAiAnalysisRepository,
    NewsArticleRepository,
    NewsKeywordRepository,
    NewsStockLinkRepository,
)
from ..models import NewsAiAnalysis, NewsArticle, NewsKeyword, NewsStockLink

if TYPE_CHECKING:
    from datetime import date


class DjangoNewsArticleRepository(NewsArticleRepository):
    """ニュース記事リポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: NewsArticle) -> NewsArticleEntity:
        return NewsArticleEntity(
            id=obj.pk,
            source=obj.source,
            source_article_id=obj.source_article_id,
            category=obj.category,
            title=obj.title,
            url=obj.url,
            summary=obj.summary,
            publisher=obj.publisher or None,
            language=obj.language,
            published_at=obj.published_at,
            fetched_at=obj.fetched_at,
            ai_analyzed_at=obj.ai_analyzed_at,
            importance_score=(Decimal(str(obj.importance_score)) if obj.importance_score is not None else None),
        )

    def find_by_id(self, news_id: int) -> NewsArticleEntity | None:
        obj = NewsArticle.objects.filter(pk=news_id).first()
        return self._to_entity(obj) if obj else None

    def find_by_source_article_id(self, source: str, source_article_id: str) -> NewsArticleEntity | None:
        obj = NewsArticle.objects.filter(source=source, source_article_id=source_article_id).first()
        return self._to_entity(obj) if obj else None

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
        qs = NewsArticle.objects.all()
        if category:
            qs = qs.filter(category=category)
        if date_from:
            qs = qs.filter(published_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(published_at__date__lte=date_to)
        if keyword:
            qs = qs.filter(Q(title__icontains=keyword) | Q(summary__icontains=keyword))
        if stock_id is not None:
            qs = qs.filter(stock_links__stock_id=stock_id)
        qs = qs.order_by("-published_at").distinct()
        total = qs.count()
        if limit is not None:
            qs = qs[offset : offset + limit]
        elif offset:
            qs = qs[offset:]
        return [self._to_entity(obj) for obj in qs], total

    def list_articles_for_stocks(
        self,
        *,
        stock_ids: list[int],
        days: int = 7,
        min_importance: Decimal | None = None,
        limit: int = 20,
    ) -> tuple[list[NewsArticleEntity], int]:
        if not stock_ids:
            return [], 0

        from datetime import UTC, datetime, timedelta

        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        qs = NewsArticle.objects.filter(
            stock_links__stock_id__in=stock_ids,
            published_at__gte=cutoff,
        )
        if min_importance is not None:
            qs = qs.filter(importance_score__gte=min_importance)
        qs = qs.order_by("-published_at").distinct()
        total = qs.count()
        qs = qs[:limit]
        return [self._to_entity(obj) for obj in qs], total

    def save(self, entity: NewsArticleEntity) -> NewsArticleEntity:
        defaults = {
            "category": entity.category,
            "title": entity.title,
            "url": entity.url,
            "summary": entity.summary,
            "publisher": entity.publisher or "",
            "language": entity.language,
            "published_at": entity.published_at,
            "importance_score": entity.importance_score,
        }
        if entity.ai_analyzed_at is not None:
            defaults["ai_analyzed_at"] = entity.ai_analyzed_at
        obj, _ = NewsArticle.objects.update_or_create(
            source=entity.source,
            source_article_id=entity.source_article_id,
            defaults=defaults,
        )
        return self._to_entity(obj)


class DjangoNewsStockLinkRepository(NewsStockLinkRepository):
    """ニュース × 銘柄リンクリポジトリ Django ORM 実装"""

    def bulk_save(self, entities: list[NewsStockLinkEntity]) -> int:
        if not entities:
            return 0
        objs = [
            NewsStockLink(
                news_id=e.news_id,
                stock_id=e.stock_id,
                relevance_score=e.relevance_score,
                matched_by=e.matched_by,
            )
            for e in entities
        ]
        created = NewsStockLink.objects.bulk_create(objs, ignore_conflicts=True)
        return len(created)

    def find_stock_ids_by_news_id(self, news_id: int) -> list[int]:
        return list(NewsStockLink.objects.filter(news_id=news_id).values_list("stock_id", flat=True))


class DjangoNewsAiAnalysisRepository(NewsAiAnalysisRepository):
    """ニュース AI 分析結果リポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: NewsAiAnalysis) -> NewsAiAnalysisEntity:
        return NewsAiAnalysisEntity(
            id=obj.pk,
            news_id=obj.news_id,
            user_id=obj.user_id,
            impact_direction=obj.impact_direction,
            impact_period=obj.impact_period,
            confidence=obj.confidence,
            affected_targets=list(obj.affected_targets or []),
            reasoning=obj.reasoning,
            key_points=list(obj.key_points or []),
            model_used=obj.model_used,
            prompt_tokens=obj.prompt_tokens,
            completion_tokens=obj.completion_tokens,
            generated_at=obj.generated_at,
        )

    def find_batch_by_news_id(self, news_id: int) -> NewsAiAnalysisEntity | None:
        obj = NewsAiAnalysis.objects.filter(news_id=news_id, user__isnull=True).order_by("-generated_at").first()
        return self._to_entity(obj) if obj else None

    def save(self, entity: NewsAiAnalysisEntity) -> NewsAiAnalysisEntity:
        from datetime import UTC, datetime

        generated_at = entity.generated_at or datetime.now(tz=UTC)
        obj = NewsAiAnalysis.objects.create(
            news_id=entity.news_id,
            user_id=entity.user_id,
            impact_direction=entity.impact_direction,
            impact_period=entity.impact_period,
            confidence=entity.confidence,
            affected_targets=entity.affected_targets,
            reasoning=entity.reasoning,
            key_points=entity.key_points,
            model_used=entity.model_used,
            prompt_tokens=entity.prompt_tokens,
            completion_tokens=entity.completion_tokens,
            generated_at=generated_at,
        )
        return self._to_entity(obj)


class DjangoNewsKeywordRepository(NewsKeywordRepository):
    """ニュース検索キーワードリポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: NewsKeyword) -> NewsKeywordEntity:
        return NewsKeywordEntity(
            id=obj.pk,
            category=obj.category,
            keyword=obj.keyword,
            query=obj.query,
            is_active=obj.is_active,
            sort_order=obj.sort_order,
        )

    def find_active_by_category(self, category: str) -> list[NewsKeywordEntity]:
        qs = NewsKeyword.objects.filter(category=category, is_active=True).order_by("sort_order")
        return [self._to_entity(obj) for obj in qs]
