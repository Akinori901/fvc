"""ニュース機能ドメインエンティティの単体テスト。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from apps.news.domain.entities import (
    CATEGORY_STOCK,
    MATCHED_BY_NAME_EXACT,
    SOURCE_GOOGLE_NEWS_RSS,
    NewsAiAnalysisEntity,
    NewsArticleEntity,
    NewsStockLinkEntity,
)


class TestNewsArticleEntity:
    def test_minimum_construction(self) -> None:
        entity = NewsArticleEntity(
            source=SOURCE_GOOGLE_NEWS_RSS,
            source_article_id="abc-123",
            category=CATEGORY_STOCK,
            title="トヨタ、Q3決算で営業益2割増",
            url="https://example.com/a",
            published_at=datetime(2026, 5, 13, 9, 0, tzinfo=UTC),
        )
        assert entity.id is None
        assert entity.summary == ""
        assert entity.publisher is None
        assert entity.language == "ja"
        assert entity.importance_score is None

    def test_full_construction(self) -> None:
        entity = NewsArticleEntity(
            source=SOURCE_GOOGLE_NEWS_RSS,
            source_article_id="abc-123",
            category=CATEGORY_STOCK,
            title="t",
            url="u",
            summary="s",
            publisher="日経",
            language="ja",
            published_at=datetime(2026, 5, 13, tzinfo=UTC),
            importance_score=Decimal("75.50"),
        )
        assert entity.publisher == "日経"
        assert entity.importance_score == Decimal("75.50")


class TestNewsStockLinkEntity:
    def test_construction(self) -> None:
        link = NewsStockLinkEntity(
            news_id=1,
            stock_id=42,
            relevance_score=Decimal("1.0"),
            matched_by=MATCHED_BY_NAME_EXACT,
        )
        assert link.news_id == 1
        assert link.stock_id == 42
        assert link.relevance_score == Decimal("1.0")


class TestNewsAiAnalysisEntity:
    def test_default_lists(self) -> None:
        entity = NewsAiAnalysisEntity(
            news_id=1,
            impact_direction="positive",
            impact_period="short",
            confidence="medium",
            reasoning="r",
            model_used="gpt-4o-mini",
        )
        assert entity.affected_targets == []
        assert entity.key_points == []
        assert entity.user_id is None

    def test_user_id_separates_batch_vs_on_demand(self) -> None:
        batch = NewsAiAnalysisEntity(
            news_id=1,
            impact_direction="neutral",
            impact_period="long",
            confidence="low",
            reasoning="r",
            model_used="m",
        )
        on_demand = NewsAiAnalysisEntity(
            news_id=1,
            impact_direction="neutral",
            impact_period="long",
            confidence="low",
            reasoning="r",
            model_used="m",
            user_id=99,
        )
        assert batch.user_id is None
        assert on_demand.user_id == 99
