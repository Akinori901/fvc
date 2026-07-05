"""会社名・コードからの曖昧検索ツール UseCase。"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import StockRepository


_VALID_INSTRUMENT_TYPES = frozenset({"all", "stock", "etf", "reit", "other"})
_VALID_MARKET_TYPES = frozenset({"JP", "US"})
_LIMIT_HARD_CAP = 50


class SearchTickerToolUseCase:
    """会社名・コード文字列から銘柄候補を返す。

    LLM が「yutori」のような曖昧入力を受けたとき、銘柄コードに解決するために使う。
    """

    def __init__(self, stock_repo: StockRepository) -> None:
        self._stock_repo = stock_repo

    def execute(
        self,
        *,
        query: str,
        instrument_type: str = "all",
        market_type: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        normalized = unicodedata.normalize("NFKC", query).strip()
        if not normalized:
            raise ValueError("query は必須です（空文字は不可）")

        if instrument_type not in _VALID_INSTRUMENT_TYPES:
            raise ValueError(f"instrument_type は {sorted(_VALID_INSTRUMENT_TYPES)} のいずれか")
        if market_type is not None and market_type not in _VALID_MARKET_TYPES:
            raise ValueError(f"market_type は {sorted(_VALID_MARKET_TYPES)} のいずれか")

        effective_limit = max(1, min(limit, _LIMIT_HARD_CAP))
        repo_instrument_type = None if instrument_type == "all" else instrument_type

        results = self._stock_repo.search_by_name(
            normalized,
            instrument_type=repo_instrument_type,
            market_type=market_type,
            limit=effective_limit,
        )

        items = [
            {
                "code": s.code,
                "name": s.name,
                "instrument_type": s.instrument_type,
                "market": s.market,
                "market_type": s.market_type,
            }
            for s in results
        ]

        return {
            "count": len(items),
            "query": normalized,
            "items": items,
        }
