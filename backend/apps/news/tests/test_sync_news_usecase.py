"""SyncNewsUseCase の単体テスト（依存はモック、DBアクセスなし）。

`_sync_one_stock` に `@transaction.atomic` デコレータが付いているが、
呼び出し時に Django の DB connection を要求するため、テスト時は
クラスメソッドを直接 unwrap して呼ぶ形にする。
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.news.application.dto import MatchedStockDTO, NewsItemDTO
from apps.news.application.usecases.sync_news_usecase import SyncNewsUseCase
from apps.news.domain.entities import (
    CATEGORY_MARKET,
    CATEGORY_STOCK,
    SOURCE_GOOGLE_NEWS_RSS,
    NewsArticleEntity,
)
from apps.stocks.domain.entities import StockEntity


def _stock(id_: int, code: str, name: str) -> StockEntity:
    return StockEntity(
        id=id_,
        code=code,
        name=name,
        market_type="JP",
        market="prime",
        sector="その他",
        is_active=True,
    )


def _item(article_id: str, title: str = "トヨタ自動車決算") -> NewsItemDTO:
    return NewsItemDTO(
        source=SOURCE_GOOGLE_NEWS_RSS,
        source_article_id=article_id,
        title=title,
        url=f"https://example.com/{article_id}",
        summary="",
        publisher=None,
        language="ja",
        published_at=datetime(2026, 5, 13, tzinfo=UTC),
    )


def _saved_entity(item: NewsItemDTO, news_id: int = 1) -> NewsArticleEntity:
    return NewsArticleEntity(
        id=news_id,
        source=item.source,
        source_article_id=item.source_article_id,
        category=CATEGORY_STOCK,
        title=item.title,
        url=item.url,
        published_at=item.published_at,
        importance_score=Decimal("50"),
    )


def _build_usecase(
    *,
    google_news_items: list[NewsItemDTO],
    target_stock: StockEntity,
    upsert_returns: list[tuple[NewsArticleEntity, int, bool]],
) -> tuple[SyncNewsUseCase, dict[str, Any]]:
    google_client = MagicMock()
    google_client.fetch.return_value = google_news_items

    matching = MagicMock()
    matching.match.return_value = [
        MatchedStockDTO(stock_id=target_stock.id or 1, relevance_score=1.0, matched_by="name_exact_with_context")
    ]

    importance = MagicMock()
    importance.compute.return_value = Decimal("50")

    sync_service = MagicMock()
    sync_service.upsert_article_with_links.side_effect = upsert_returns

    stock_repo = MagicMock()
    stock_repo.find_by_code.return_value = target_stock
    stock_repo.find_by_market_type.return_value = [target_stock]

    usecase = SyncNewsUseCase(
        google_news_client=google_client,
        matching_service=matching,
        importance_service=importance,
        sync_service=sync_service,
        stock_repo=stock_repo,
    )
    return usecase, {
        "google_client": google_client,
        "matching": matching,
        "sync_service": sync_service,
        "stock_repo": stock_repo,
    }


@pytest.fixture(autouse=True)
def _noop_atomic():  # type: ignore[no-untyped-def]
    """transaction.atomic を no-op にして DB アクセスを回避する。"""
    from contextlib import contextmanager

    @contextmanager
    def noop():  # type: ignore[no-untyped-def]
        yield

    with patch(
        "apps.news.application.usecases.sync_news_usecase.transaction.atomic",
        side_effect=lambda: noop(),
    ):
        yield


class TestSyncNewsUseCase:
    def test_invalid_category_raises(self) -> None:
        usecase, _ = _build_usecase(google_news_items=[], target_stock=_stock(1, "7203", "トヨタ"), upsert_returns=[])
        with pytest.raises(ValueError):
            usecase.execute(category="invalid")

    def test_market_category_not_implemented_in_phase1(self) -> None:
        usecase, _ = _build_usecase(google_news_items=[], target_stock=_stock(1, "7203", "トヨタ"), upsert_returns=[])
        with pytest.raises(NotImplementedError):
            usecase.execute(category=CATEGORY_MARKET)

    def test_code_not_found_raises(self) -> None:
        usecase, mocks = _build_usecase(
            google_news_items=[], target_stock=_stock(1, "7203", "トヨタ"), upsert_returns=[]
        )
        mocks["stock_repo"].find_by_code.return_value = None
        with pytest.raises(ValueError):
            usecase.execute(category=CATEGORY_STOCK, code="9999")

    def test_new_article_counted_in_saved(self) -> None:
        stock = _stock(1, "7203", "トヨタ自動車")
        item1 = _item("g-1")
        item2 = _item("g-2")
        usecase, mocks = _build_usecase(
            google_news_items=[item1, item2],
            target_stock=stock,
            upsert_returns=[
                (_saved_entity(item1, 1), 1, True),
                (_saved_entity(item2, 2), 1, True),
            ],
        )
        with patch("apps.news.application.usecases.sync_news_usecase.time.sleep"):
            result = usecase.execute(category=CATEGORY_STOCK, code="7203")
        assert result.fetched == 2
        assert result.saved == 2
        assert result.matched_links == 2

    def test_duplicate_article_not_counted_as_new(self) -> None:
        """既存記事（is_new=False）は saved にカウントされない。"""
        stock = _stock(1, "7203", "トヨタ自動車")
        item1 = _item("g-1")
        usecase, _ = _build_usecase(
            google_news_items=[item1],
            target_stock=stock,
            upsert_returns=[(_saved_entity(item1, 1), 0, False)],
        )
        with patch("apps.news.application.usecases.sync_news_usecase.time.sleep"):
            result = usecase.execute(category=CATEGORY_STOCK, code="7203")
        assert result.fetched == 1
        assert result.saved == 0  # 重複なので増えない
        assert result.matched_links == 0  # 既存リンクは bulk_save の ignore_conflicts で 0

    def test_irrelevant_article_skipped(self) -> None:
        """対象銘柄がマッチに含まれていない記事はスキップされる（誤検知抑制）。"""
        stock = _stock(1, "7203", "トヨタ自動車")
        item1 = _item("g-1", title="ホンダ決算")
        usecase, mocks = _build_usecase(
            google_news_items=[item1],
            target_stock=stock,
            upsert_returns=[],
        )
        # match は別銘柄を返す
        mocks["matching"].match.return_value = [
            MatchedStockDTO(stock_id=999, relevance_score=1.0, matched_by="name_exact")
        ]
        with patch("apps.news.application.usecases.sync_news_usecase.time.sleep"):
            result = usecase.execute(category=CATEGORY_STOCK, code="7203")
        assert result.fetched == 1
        assert result.saved == 0
        assert result.skipped_irrelevant == 1
        mocks["sync_service"].upsert_article_with_links.assert_not_called()
