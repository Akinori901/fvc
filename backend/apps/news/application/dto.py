"""ニュース機能 DTO。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class NewsItemDTO:
    """外部ソースから取得した未整形ニュース項目"""

    source: str
    source_article_id: str
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    publisher: str | None = None
    language: str = "ja"


@dataclass
class MatchedStockDTO:
    """銘柄マッチ結果"""

    stock_id: int
    relevance_score: float
    matched_by: str


@dataclass
class SyncNewsResultDTO:
    """sync_news 実行結果"""

    fetched: int = 0
    saved: int = 0
    matched_links: int = 0
    skipped_irrelevant: int = 0
    errors: list[str] = field(default_factory=list)
