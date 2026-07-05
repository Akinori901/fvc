"""ニュース一覧取得ユースケース（全カテゴリ・フィルタ付き）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from ...domain.entities import NewsArticleEntity
    from ...domain.repositories import NewsArticleRepository


class ListNewsUseCase:
    """ニュース一覧取得"""

    def __init__(self, article_repo: NewsArticleRepository) -> None:
        self._article_repo = article_repo

    def execute(
        self,
        *,
        category: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        keyword: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NewsArticleEntity], int]:
        return self._article_repo.list_articles(
            category=category,
            date_from=date_from,
            date_to=date_to,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
