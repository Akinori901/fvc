"""ニュース重要度スコア算出サービス。

設計書 §5.3 のヒューリスティック:
- base = 20
- category boost: earnings=30, fx=20, market=20, stock=10
- publisher boost: 日経/Reuters/Bloomberg=15, その他=5
- keyword boost: 「決算」「業績修正」「FOMC」「日銀」「介入」=15
- stock match boost: relevance_score >= 0.9 紐付き=10
- recency: 24h以内=10, 7d以内=5
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from ...domain.entities import CATEGORY_EARNINGS, CATEGORY_FX, CATEGORY_MARKET, CATEGORY_STOCK

if TYPE_CHECKING:
    from ..dto import MatchedStockDTO, NewsItemDTO

_BASE_SCORE = Decimal("20")

_CATEGORY_BOOSTS = {
    CATEGORY_EARNINGS: Decimal("30"),
    CATEGORY_FX: Decimal("20"),
    CATEGORY_MARKET: Decimal("20"),
    CATEGORY_STOCK: Decimal("10"),
}

_PUBLISHER_HIGH_TRUST_KEYWORDS = (
    "日本経済新聞",
    "日経",
    "Reuters",
    "ロイター",
    "Bloomberg",
    "ブルームバーグ",
)

_HOT_KEYWORDS = (
    "決算",
    "業績修正",
    "上方修正",
    "下方修正",
    "FOMC",
    "日銀",
    "為替介入",
    "利上げ",
    "利下げ",
)


class NewsImportanceService:
    """重要度スコア計算"""

    def compute(
        self,
        *,
        item: NewsItemDTO,
        category: str,
        matched_stocks: list[MatchedStockDTO],
        now: datetime | None = None,
    ) -> Decimal:
        """importance_score を 0〜100 で返す。"""
        if now is None:
            now = datetime.now(tz=UTC)

        score = _BASE_SCORE

        # category boost
        score += _CATEGORY_BOOSTS.get(category, Decimal("0"))

        # publisher boost
        if item.publisher and any(kw in item.publisher for kw in _PUBLISHER_HIGH_TRUST_KEYWORDS):
            score += Decimal("15")
        else:
            score += Decimal("5")

        # keyword boost
        text = f"{item.title} {item.summary}"
        if any(kw in text for kw in _HOT_KEYWORDS):
            score += Decimal("15")

        # stock match boost
        if any(m.relevance_score >= 0.9 for m in matched_stocks):
            score += Decimal("10")

        # recency
        published = item.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        delta = now - published
        if delta <= timedelta(hours=24):
            score += Decimal("10")
        elif delta <= timedelta(days=7):
            score += Decimal("5")

        # clamp [0, 100]
        if score < 0:
            score = Decimal("0")
        if score > 100:
            score = Decimal("100")
        return score
