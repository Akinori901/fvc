"""ニュース機能シリアライザー。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import serializers

from ..domain.entities import VALID_CATEGORIES

if TYPE_CHECKING:
    from ..domain.entities import NewsArticleEntity


class NewsListFilterSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """GET /api/news/ のクエリパラメータ"""

    category = serializers.ChoiceField(choices=list(VALID_CATEGORIES), required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    keyword = serializers.CharField(required=False, allow_blank=True, max_length=100)


def news_entity_to_dict(entity: NewsArticleEntity) -> dict[str, Any]:
    """NewsArticleEntity → API レスポンス用 dict"""
    return {
        "id": entity.id,
        "source": entity.source,
        "category": entity.category,
        "title": entity.title,
        "url": entity.url,
        "summary": entity.summary,
        "publisher": entity.publisher,
        "language": entity.language,
        "published_at": entity.published_at.isoformat() if entity.published_at else None,
        "fetched_at": entity.fetched_at.isoformat() if entity.fetched_at else None,
        "ai_analyzed_at": entity.ai_analyzed_at.isoformat() if entity.ai_analyzed_at else None,
        "importance_score": (str(entity.importance_score) if entity.importance_score is not None else None),
    }
