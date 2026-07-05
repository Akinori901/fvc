"""NewsImportanceService の単体テスト（スコア境界値）。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from apps.news.application.dto import MatchedStockDTO, NewsItemDTO
from apps.news.application.services.news_importance_service import NewsImportanceService
from apps.news.domain.entities import (
    CATEGORY_EARNINGS,
    CATEGORY_FX,
    CATEGORY_MARKET,
    CATEGORY_STOCK,
    MATCHED_BY_NAME_EXACT_WITH_CONTEXT,
    SOURCE_GOOGLE_NEWS_RSS,
)


def _item(
    *,
    title: str = "通常タイトル",
    summary: str = "",
    publisher: str | None = "その他媒体",
    published_at: datetime | None = None,
) -> NewsItemDTO:
    return NewsItemDTO(
        source=SOURCE_GOOGLE_NEWS_RSS,
        source_article_id="x",
        title=title,
        url="https://example.com",
        summary=summary,
        publisher=publisher,
        language="ja",
        published_at=published_at or datetime(2026, 5, 13, tzinfo=UTC),
    )


FIXED_NOW = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class TestNewsImportanceService:
    def setup_method(self) -> None:
        self.service = NewsImportanceService()

    def test_base_plus_minimal(self) -> None:
        """stock=10 + その他publisher=5 + 24h以内=10 → 20+10+5+10=45。"""
        score = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        assert score == Decimal("45")

    def test_earnings_category_boost(self) -> None:
        """earnings=30 boost。"""
        score = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_EARNINGS,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 30 + 5 + 10 = 65
        assert score == Decimal("65")

    def test_fx_category_boost(self) -> None:
        score = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_FX,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 20 + 5 + 10 = 55
        assert score == Decimal("55")

    def test_market_category_boost(self) -> None:
        score = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_MARKET,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        assert score == Decimal("55")

    def test_high_trust_publisher_adds_15(self) -> None:
        score = self.service.compute(
            item=_item(publisher="日本経済新聞", published_at=FIXED_NOW),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 10 + 15 + 10 = 55
        assert score == Decimal("55")

    def test_keyword_boost(self) -> None:
        score = self.service.compute(
            item=_item(title="トヨタが業績修正", published_at=FIXED_NOW),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 10 + 5 + 15(keyword) + 10 = 60
        assert score == Decimal("60")

    def test_stock_match_boost_only_when_relevance_0_9_or_higher(self) -> None:
        score_high = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_STOCK,
            matched_stocks=[MatchedStockDTO(stock_id=1, relevance_score=0.9, matched_by="ticker")],
            now=FIXED_NOW,
        )
        # 20 + 10 + 5 + 10(stock_match) + 10 = 55
        assert score_high == Decimal("55")

        score_low = self.service.compute(
            item=_item(published_at=FIXED_NOW),
            category=CATEGORY_STOCK,
            matched_stocks=[MatchedStockDTO(stock_id=1, relevance_score=0.6, matched_by="name_exact")],
            now=FIXED_NOW,
        )
        # 0.6 → no stock_match boost → 45
        assert score_low == Decimal("45")

    def test_recency_7d_within_adds_5(self) -> None:
        published = FIXED_NOW - timedelta(days=3)
        score = self.service.compute(
            item=_item(published_at=published),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 10 + 5 + 5(7d) = 40
        assert score == Decimal("40")

    def test_old_article_no_recency_boost(self) -> None:
        published = FIXED_NOW - timedelta(days=30)
        score = self.service.compute(
            item=_item(published_at=published),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # 20 + 10 + 5 = 35
        assert score == Decimal("35")

    def test_score_clamped_to_100(self) -> None:
        score = self.service.compute(
            item=_item(
                title="決算 業績修正 FOMC 日銀",
                publisher="日経",
                published_at=FIXED_NOW,
            ),
            category=CATEGORY_EARNINGS,
            matched_stocks=[
                MatchedStockDTO(stock_id=1, relevance_score=1.0, matched_by=MATCHED_BY_NAME_EXACT_WITH_CONTEXT)
            ],
            now=FIXED_NOW,
        )
        # 20 + 30 + 15 + 15 + 10 + 10 = 100
        assert score == Decimal("100")

    def test_naive_published_at_treated_as_utc(self) -> None:
        naive = datetime(2026, 5, 13, 12, 0)  # naive
        score = self.service.compute(
            item=_item(published_at=naive),
            category=CATEGORY_STOCK,
            matched_stocks=[],
            now=FIXED_NOW,
        )
        # naive を UTC として扱うので 24h 以内に該当 → 45
        assert score == Decimal("45")
