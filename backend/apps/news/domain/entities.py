"""ニュース機能ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


# カテゴリ定数
CATEGORY_STOCK = "stock"
CATEGORY_MARKET = "market"
CATEGORY_FX = "fx"
CATEGORY_EARNINGS = "earnings"

VALID_CATEGORIES = (CATEGORY_STOCK, CATEGORY_MARKET, CATEGORY_FX, CATEGORY_EARNINGS)

# ソース定数
SOURCE_GOOGLE_NEWS_RSS = "google_news_rss"
SOURCE_YFINANCE = "yfinance"
SOURCE_JQUANTS = "jquants"

# マッチ種別
MATCHED_BY_NAME_EXACT_WITH_CONTEXT = "name_exact_with_context"
MATCHED_BY_NAME_EXACT = "name_exact"
MATCHED_BY_TICKER = "ticker"
MATCHED_BY_NAME_PARTIAL = "name_partial"
MATCHED_BY_AI_INFERRED = "ai_inferred"


@dataclass
class NewsArticleEntity:
    """ニュース記事エンティティ"""

    source: str
    source_article_id: str
    category: str
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    publisher: str | None = None
    language: str = "ja"
    fetched_at: datetime | None = None
    ai_analyzed_at: datetime | None = None
    importance_score: Decimal | None = None
    id: int | None = None


@dataclass
class NewsStockLinkEntity:
    """ニュース × 銘柄リンクエンティティ"""

    news_id: int
    stock_id: int
    relevance_score: Decimal
    matched_by: str
    id: int | None = None


@dataclass
class NewsAiAnalysisEntity:
    """ニュース AI 分析結果エンティティ"""

    news_id: int
    impact_direction: str  # positive / negative / neutral / mixed
    impact_period: str  # short / medium / long
    confidence: str  # high / medium / low
    reasoning: str
    model_used: str
    user_id: int | None = None  # NULL = バッチ事前分析
    affected_targets: list[str] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generated_at: datetime | None = None
    id: int | None = None


@dataclass
class NewsKeywordEntity:
    """市場・FX 用検索キーワードエンティティ"""

    category: str
    keyword: str
    query: str
    is_active: bool = True
    sort_order: int = 0
    id: int | None = None
