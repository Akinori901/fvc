"""ニュース API の統合テスト（認証・ページネーション・フィルタ）。

注: テスト用 MySQL DB の作成権限が必要。
ローカル環境で `fvc_user` に CREATE DATABASE 権限が無い場合は、
MySQL root から `GRANT ALL ON test_*.* TO 'fvc_user'@'%';` で権限付与してから実行する。
権限不足を自動回避するため SKIP_DB_TESTS=1 でスキップ可能。
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.news.infrastructure.models import NewsArticle, NewsStockLink
from apps.stocks.models import Stock

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS") == "1",
    reason="DB アクセスが必要なテストはスキップ（SKIP_DB_TESTS=1）",
)


def _make_article(
    *,
    source_article_id: str,
    title: str = "title",
    category: str = "stock",
    publisher: str = "Test",
    published_at: datetime | None = None,
    importance: Decimal = Decimal("50"),
) -> NewsArticle:
    return NewsArticle.objects.create(
        source="google_news_rss",
        source_article_id=source_article_id,
        category=category,
        title=title,
        url=f"https://example.com/{source_article_id}",
        summary="summary",
        publisher=publisher,
        language="ja",
        published_at=published_at or datetime(2026, 5, 13, tzinfo=UTC),
        importance_score=importance,
    )


@pytest.fixture
def auth_client(db) -> APIClient:  # type: ignore[no-untyped-def]
    user = get_user_model().objects.create_user(username="tester", password="pw1234")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestNewsListView:
    def test_requires_authentication(self) -> None:
        client = APIClient()
        resp = client.get("/api/news/")
        assert resp.status_code == 401

    def test_returns_paginated_results(self, auth_client: APIClient) -> None:
        for i in range(25):
            _make_article(source_article_id=f"a-{i}", title=f"t{i}")

        resp = auth_client.get("/api/news/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 25
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["results"]) == 20

        # 2ページ目
        resp2 = auth_client.get("/api/news/?page=2")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["page"] == 2
        assert len(body2["results"]) == 5

    def test_filter_by_category(self, auth_client: APIClient) -> None:
        _make_article(source_article_id="s1", category="stock")
        _make_article(source_article_id="m1", category="market")

        resp = auth_client.get("/api/news/?category=stock")
        body = resp.json()
        assert body["count"] == 1
        assert body["results"][0]["category"] == "stock"

    def test_filter_by_keyword(self, auth_client: APIClient) -> None:
        _make_article(source_article_id="k1", title="トヨタ決算")
        _make_article(source_article_id="k2", title="ホンダ業績")

        resp = auth_client.get("/api/news/?keyword=トヨタ")
        body = resp.json()
        assert body["count"] == 1

    def test_invalid_category_returns_400(self, auth_client: APIClient) -> None:
        resp = auth_client.get("/api/news/?category=invalid")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestStockNewsView:
    def test_returns_only_linked_articles(self, auth_client: APIClient) -> None:
        stock = Stock.objects.create(code="7203", name="トヨタ自動車")
        other = Stock.objects.create(code="6758", name="ソニーG")

        a1 = _make_article(source_article_id="a-1", title="トヨタ決算")
        _make_article(source_article_id="a-2", title="ソニー決算")
        a3 = _make_article(source_article_id="a-3", title="トヨタ新工場")

        NewsStockLink.objects.create(news=a1, stock=stock, relevance_score=Decimal("1.0"), matched_by="name_exact")
        NewsStockLink.objects.create(news=a3, stock=stock, relevance_score=Decimal("0.6"), matched_by="name_exact")
        # other に紐付くリンクは無視
        _ = other

        resp = auth_client.get("/api/news/stocks/7203/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 2
        titles = sorted(r["title"] for r in body["results"])
        assert titles == ["トヨタ新工場", "トヨタ決算"]

    def test_unknown_code_returns_404(self, auth_client: APIClient) -> None:
        resp = auth_client.get("/api/news/stocks/0000/")
        assert resp.status_code == 404
