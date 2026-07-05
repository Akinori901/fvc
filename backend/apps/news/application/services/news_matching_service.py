"""ニュース × 銘柄マッチングサービス。

設計書 §5.2 の 4 段階スコア戦略:
- 完全一致 + 株式関連語共起: 1.0  → name_exact_with_context
- ティッカーコード一致: 0.9       → ticker
- 完全一致のみ: 0.6                → name_exact
- 部分一致: 0.4                    → name_partial（DB登録対象外）

`relevance_score >= 0.6` のみマッチとして返す。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...domain.entities import (
    MATCHED_BY_NAME_EXACT,
    MATCHED_BY_NAME_EXACT_WITH_CONTEXT,
    MATCHED_BY_TICKER,
)
from ..dto import MatchedStockDTO

if TYPE_CHECKING:
    from apps.stocks.domain.entities import StockEntity


# 社名末尾のサフィックス（マッチ用に正規化して取り除く）
_SUFFIX_PATTERNS = [
    "株式会社",
    "(株)",
    "（株）",
    "ホールディングス",
    "ＨＤ",
    "HD",
    "グループ",
]

# 株式関連の共起語（含まれていれば信頼度上昇）
_CONTEXT_KEYWORDS = (
    "株価",
    "決算",
    "業績",
    "時価総額",
    "IR",
    "上方修正",
    "下方修正",
    "増配",
    "減配",
    "配当",
    "自社株買い",
    "TOB",
    "公募",
    "株式分割",
)


def _normalize_name(name: str) -> str:
    """社名末尾のサフィックスを取り除き、空白を除去。"""
    normalized = name
    for suffix in _SUFFIX_PATTERNS:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.strip()


class NewsMatchingService:
    """ニュースと銘柄のマッチ判定"""

    def match(self, *, text: str, candidate_stocks: list[StockEntity]) -> list[MatchedStockDTO]:
        """text（タイトル + summary）に対し candidate_stocks のうちマッチした銘柄を返す。

        relevance_score >= 0.6 のみ返す。
        """
        if not text or not candidate_stocks:
            return []

        has_context = any(kw in text for kw in _CONTEXT_KEYWORDS)
        results: list[MatchedStockDTO] = []

        for stock in candidate_stocks:
            if stock.id is None:
                continue

            normalized_name = _normalize_name(stock.name)
            if not normalized_name:
                continue

            ticker_match = _has_ticker_match(text, stock.code)
            name_match = normalized_name in text

            if name_match and has_context:
                results.append(
                    MatchedStockDTO(
                        stock_id=stock.id,
                        relevance_score=1.0,
                        matched_by=MATCHED_BY_NAME_EXACT_WITH_CONTEXT,
                    )
                )
            elif ticker_match:
                results.append(
                    MatchedStockDTO(
                        stock_id=stock.id,
                        relevance_score=0.9,
                        matched_by=MATCHED_BY_TICKER,
                    )
                )
            elif name_match:
                results.append(
                    MatchedStockDTO(
                        stock_id=stock.id,
                        relevance_score=0.6,
                        matched_by=MATCHED_BY_NAME_EXACT,
                    )
                )

        return results


def _has_ticker_match(text: str, code: str) -> bool:
    """ティッカーコード「7203」「7203.T」が独立した語として text に出現するか。"""
    if not code:
        return False
    # 数字のみのコード（日本株）は単語境界で囲む
    if code.isdigit():
        return bool(re.search(rf"(?<!\d){re.escape(code)}(?:\.T)?(?!\d)", text))
    # 米国株のような英字を含むコード（AAPL 等）
    return bool(re.search(rf"\b{re.escape(code)}\b", text))
