"""信頼ソース URL 取得ツール UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import StockRepository

    from ...services.news_source_url_builder_service import NewsSourceUrlBuilderService


class SearchStockNewsSourcesToolUseCase:
    """銘柄に関する信頼ソース（日経・TDnet・EDINET 等）の検索 URL を返す。

    実際の記事取得は行わない。Claude / ChatGPT が WebFetch で読みに行く想定。
    """

    def __init__(
        self,
        stock_repo: StockRepository,
        url_builder: NewsSourceUrlBuilderService,
    ) -> None:
        self._stock_repo = stock_repo
        self._url_builder = url_builder

    def execute(self, *, code: str, query: str | None = None) -> dict[str, Any]:
        stock = self._stock_repo.find_by_code(code)
        if stock is None:
            raise ValueError(f"銘柄が見つかりません: {code}")

        sources = self._url_builder.build(stock_name=stock.name, query=query)
        return {
            "code": stock.code,
            "stock_name": stock.name,
            "query_used": query or stock.name,
            "sources": sources,
            "hint": (
                "primary = 一次情報源（公式開示・公式リリース）、"
                "secondary = 報道機関の検索結果。WebFetch で記事本文を取得して分析に活用してください。"
            ),
        }
