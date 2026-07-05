"""NewsSourceUrlBuilderService の単体テスト。"""

from __future__ import annotations

from apps.mcp.application.services.news_source_url_builder_service import (
    NewsSourceUrlBuilderService,
)


class TestNewsSourceUrlBuilderService:
    def setup_method(self) -> None:
        self.service = NewsSourceUrlBuilderService()

    def test_returns_primary_and_secondary(self) -> None:
        sources = self.service.build(stock_name="トヨタ自動車")
        tiers = {s["tier"] for s in sources}
        assert "primary" in tiers
        assert "secondary" in tiers

    def test_nikkei_url_includes_query(self) -> None:
        sources = self.service.build(stock_name="トヨタ自動車")
        nikkei = next(s for s in sources if s["name"] == "日本経済新聞")
        assert "%E3%83%88%E3%83%A8%E3%82%BF" in nikkei["url"]  # トヨ encoded

    def test_query_overrides_stock_name(self) -> None:
        sources = self.service.build(stock_name="トヨタ自動車", query="自動運転")
        nikkei = next(s for s in sources if s["name"] == "日本経済新聞")
        # "自動運転" がエンコードされて URL に入る
        assert "%E8%87%AA%E5%8B%95%E9%81%8B%E8%BB%A2" in nikkei["url"]

    def test_empty_query_returns_empty(self) -> None:
        assert self.service.build(stock_name="") == []
        assert self.service.build(stock_name="", query="") == []

    def test_tdnet_url_returned(self) -> None:
        sources = self.service.build(stock_name="ABC株式会社")
        assert any("tdnet.info" in s["url"] for s in sources)
