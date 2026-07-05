"""特定銘柄に紐付くニュース一覧取得ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import StockRepository

    from ...domain.entities import NewsArticleEntity
    from ...domain.repositories import NewsArticleRepository


class ListStockNewsUseCase:
    """銘柄詳細タブ用: stock_code → ニュース一覧"""

    def __init__(
        self,
        article_repo: NewsArticleRepository,
        stock_repo: StockRepository,
    ) -> None:
        self._article_repo = article_repo
        self._stock_repo = stock_repo

    def execute(
        self,
        *,
        code: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NewsArticleEntity], int]:
        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {code}")
        return self._article_repo.list_articles(
            stock_id=stock.id,
            limit=limit,
            offset=offset,
        )
