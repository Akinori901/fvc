"""Google News RSS クライアントサービス。

feedparser で https://news.google.com/rss/search を読み、NewsItemDTO リストを返す。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import feedparser
import httpx

from ...domain.entities import SOURCE_GOOGLE_NEWS_RSS
from ...domain.exceptions import NewsSourceError
from ..dto import NewsItemDTO

logger = logging.getLogger(__name__)

_BASE_URL = "https://news.google.com/rss/search"
_TIMEOUT = 15.0
_USER_AGENT = "fair-value-calculator-news/1.0"


class GoogleNewsRssClientService:
    """Google News RSS クライアント"""

    def __init__(self, *, timeout: float = _TIMEOUT) -> None:
        self._timeout = timeout

    def fetch(
        self,
        query: str,
        *,
        lang: str = "ja",
        country: str = "JP",
        limit: int = 50,
    ) -> list[NewsItemDTO]:
        """検索クエリに合致する RSS フィードを取得し NewsItemDTO のリストを返す。"""
        params = {
            "q": query,
            "hl": lang,
            "gl": country,
            "ceid": f"{country}:{lang}",
        }
        url = f"{_BASE_URL}?{urlencode(params)}"

        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": _USER_AGENT})
                resp.raise_for_status()
                content = resp.content
        except httpx.HTTPError as e:
            raise NewsSourceError(f"Google News RSS fetch failed for query={query!r}: {e}") from e

        feed = feedparser.parse(content)
        if feed.bozo:
            logger.warning("Google News RSS bozo (query=%s): %s", query, feed.bozo_exception)

        items: list[NewsItemDTO] = []
        for entry in feed.entries[:limit]:
            item = self._parse_entry(entry, lang=lang)
            if item is not None:
                items.append(item)

        logger.info("Google News RSS query=%r → %d items", query, len(items))
        return items

    @staticmethod
    def _parse_entry(entry: Any, *, lang: str) -> NewsItemDTO | None:
        guid: str | None = entry.get("id") or entry.get("guid") or entry.get("link")
        title: str | None = entry.get("title")
        link: str | None = entry.get("link")
        if not guid or not title or not link:
            return None

        published_at = _parse_published(entry)
        if published_at is None:
            return None

        summary = entry.get("summary", "") or ""
        publisher: str | None = None
        source = entry.get("source")
        if isinstance(source, dict):
            publisher = source.get("title")
        if not publisher:
            publisher = entry.get("author")

        return NewsItemDTO(
            source=SOURCE_GOOGLE_NEWS_RSS,
            source_article_id=guid,
            title=str(title),
            url=str(link),
            summary=str(summary),
            publisher=publisher,
            language=lang,
            published_at=published_at,
        )


def _parse_published(entry: Any) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    try:
        year, month, day, hour, minute, second = parsed[:6]
        return datetime(year, month, day, hour, minute, second, tzinfo=UTC)
    except (TypeError, ValueError):
        return None
