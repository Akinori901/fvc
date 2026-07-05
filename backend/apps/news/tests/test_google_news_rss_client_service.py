"""GoogleNewsRssClientService の単体テスト（httpx を respx でモック）。"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from apps.news.application.services.google_news_rss_client_service import (
    GoogleNewsRssClientService,
)
from apps.news.domain.entities import SOURCE_GOOGLE_NEWS_RSS
from apps.news.domain.exceptions import NewsSourceError

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Google News</title>
<item>
<title>トヨタ自動車が決算発表</title>
<link>https://example.com/a</link>
<guid isPermaLink="false">guid-001</guid>
<pubDate>Tue, 13 May 2026 09:00:00 GMT</pubDate>
<description>2026年Q3決算で営業益2割増を発表</description>
<source url="https://nikkei.com">日本経済新聞</source>
</item>
<item>
<title>関連ニュース 2</title>
<link>https://example.com/b</link>
<guid isPermaLink="false">guid-002</guid>
<pubDate>Tue, 13 May 2026 08:30:00 GMT</pubDate>
</item>
</channel>
</rss>
""".encode()


class _MockClient:
    def __init__(self, content: bytes, status_code: int = 200) -> None:
        self._content = content
        self._status_code = status_code

    def __enter__(self) -> _MockClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(self._status_code, content=self._content, request=req)


class TestGoogleNewsRssClientService:
    def test_fetch_parses_entries(self) -> None:
        service = GoogleNewsRssClientService()
        with patch("httpx.Client", lambda **_kw: _MockClient(_SAMPLE_RSS)):
            items = service.fetch("トヨタ自動車", limit=10)

        assert len(items) == 2
        first = items[0]
        assert first.source == SOURCE_GOOGLE_NEWS_RSS
        assert first.source_article_id == "guid-001"
        assert first.title == "トヨタ自動車が決算発表"
        assert first.url == "https://example.com/a"
        assert "営業益" in first.summary
        assert first.publisher == "日本経済新聞"
        assert first.language == "ja"

    def test_fetch_respects_limit(self) -> None:
        service = GoogleNewsRssClientService()
        with patch("httpx.Client", lambda **_kw: _MockClient(_SAMPLE_RSS)):
            items = service.fetch("Q", limit=1)
        assert len(items) == 1

    def test_http_error_raises_news_source_error(self) -> None:
        service = GoogleNewsRssClientService()
        with (
            patch("httpx.Client", lambda **_kw: _MockClient(b"", status_code=503)),
            pytest.raises(NewsSourceError),
        ):
            service.fetch("Q")
