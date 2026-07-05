"""Django ORM 実装のニュースリポジトリテスト。"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from apps.news.infrastructure.models import NewsArticle, NewsStockLink
from apps.news.infrastructure.repositories import DjangoNewsArticleRepository
from apps.stocks.models import Stock

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS") == "1",
    reason="DB アクセスが必要なテストはスキップ（SKIP_DB_TESTS=1）",
)


def _make_article(
    *,
    source_article_id: str,
    title: str = "title",
    published_at: datetime | None = None,
    importance: Decimal | None = Decimal("50"),
) -> NewsArticle:
    return NewsArticle.objects.create(
        source="google_news_rss",
        source_article_id=source_article_id,
        category="stock",
        title=title,
        url=f"https://example.com/{source_article_id}",
        summary="summary",
        publisher="Test",
        language="ja",
        published_at=published_at or datetime.now(tz=UTC),
        importance_score=importance,
    )


@pytest.mark.django_db
class TestDjangoNewsArticleRepositoryListArticlesForStocks:
    def setup_method(self) -> None:
        self.repo = DjangoNewsArticleRepository()

    def test_returns_articles_for_multiple_stocks(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        sony = Stock.objects.create(code="6758", name="ソニーG")
        a1 = _make_article(source_article_id="a-1", title="トヨタ決算")
        a2 = _make_article(source_article_id="a-2", title="ソニー新製品")
        a3 = _make_article(source_article_id="a-3", title="無関係ニュース")
        NewsStockLink.objects.create(news=a1, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact")
        NewsStockLink.objects.create(news=a2, stock=sony, relevance_score=Decimal("1.0"), matched_by="name_exact")
        _ = a3  # 銘柄リンクなし → 取得対象外

        entities, total = self.repo.list_articles_for_stocks(stock_ids=[toyota.pk, sony.pk])
        assert total == 2
        titles = sorted(e.title for e in entities)
        assert titles == ["ソニー新製品", "トヨタ決算"]

    def test_deduplicates_articles_linked_to_multiple_stocks(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        sony = Stock.objects.create(code="6758", name="ソニーG")
        a = _make_article(source_article_id="dup-1", title="自動車セクター動向")
        NewsStockLink.objects.create(news=a, stock=toyota, relevance_score=Decimal("0.8"), matched_by="name_exact")
        NewsStockLink.objects.create(news=a, stock=sony, relevance_score=Decimal("0.6"), matched_by="name_exact")

        entities, total = self.repo.list_articles_for_stocks(stock_ids=[toyota.pk, sony.pk])
        assert total == 1
        assert len(entities) == 1

    def test_filters_by_days(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        recent = _make_article(
            source_article_id="recent",
            title="直近",
            published_at=datetime.now(tz=UTC) - timedelta(days=2),
        )
        old = _make_article(
            source_article_id="old",
            title="古い",
            published_at=datetime.now(tz=UTC) - timedelta(days=30),
        )
        NewsStockLink.objects.create(news=recent, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact")
        NewsStockLink.objects.create(news=old, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact")

        entities, total = self.repo.list_articles_for_stocks(stock_ids=[toyota.pk], days=7)
        assert total == 1
        assert entities[0].title == "直近"

    def test_filters_by_min_importance(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        high = _make_article(source_article_id="h", title="重要", importance=Decimal("0.9"))
        low = _make_article(source_article_id="l", title="重要度低", importance=Decimal("0.3"))
        NewsStockLink.objects.create(news=high, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact")
        NewsStockLink.objects.create(news=low, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact")

        entities, total = self.repo.list_articles_for_stocks(stock_ids=[toyota.pk], min_importance=Decimal("0.5"))
        assert total == 1
        assert entities[0].title == "重要"

    def test_empty_stock_ids_returns_empty(self) -> None:
        entities, total = self.repo.list_articles_for_stocks(stock_ids=[])
        assert entities == []
        assert total == 0

    def test_respects_limit(self) -> None:
        toyota = Stock.objects.create(code="7203", name="トヨタ自動車")
        for i in range(5):
            article = _make_article(
                source_article_id=f"a-{i}",
                title=f"記事{i}",
                published_at=datetime.now(tz=UTC) - timedelta(hours=i),
            )
            NewsStockLink.objects.create(
                news=article, stock=toyota, relevance_score=Decimal("1.0"), matched_by="name_exact"
            )

        entities, total = self.repo.list_articles_for_stocks(stock_ids=[toyota.pk], limit=3)
        assert total == 5
        assert len(entities) == 3
