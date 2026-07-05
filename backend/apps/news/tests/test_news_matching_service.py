"""NewsMatchingService の単体テスト（4 段階スコア戦略）。"""

from __future__ import annotations

from apps.news.application.services.news_matching_service import NewsMatchingService
from apps.news.domain.entities import (
    MATCHED_BY_NAME_EXACT,
    MATCHED_BY_NAME_EXACT_WITH_CONTEXT,
    MATCHED_BY_TICKER,
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


class TestNewsMatchingService:
    def setup_method(self) -> None:
        self.service = NewsMatchingService()

    def test_name_exact_with_context_scores_1_0(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "トヨタ自動車が決算で増益を発表"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 1
        assert result[0].stock_id == 1
        assert result[0].relevance_score == 1.0
        assert result[0].matched_by == MATCHED_BY_NAME_EXACT_WITH_CONTEXT

    def test_name_exact_without_context_scores_0_6(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "トヨタ自動車の新工場が稼働開始"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 1
        assert result[0].relevance_score == 0.6
        assert result[0].matched_by == MATCHED_BY_NAME_EXACT

    def test_ticker_match_scores_0_9(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "7203 の出来高が急増、テクニカル指標も好転"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 1
        # context word（テクニカル指標→対象外）が無いケースだが、ティッカー一致なので 0.9
        assert result[0].relevance_score == 0.9
        assert result[0].matched_by == MATCHED_BY_TICKER

    def test_ticker_with_dot_t_suffix(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "Toyota (7203.T) reported strong earnings"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 1
        # 「earnings」は英語のため共起判定にかからない → ticker 一致のみ
        assert result[0].matched_by == MATCHED_BY_TICKER
        assert result[0].relevance_score == 0.9

    def test_partial_name_match_not_returned(self) -> None:
        """「トヨタ」だけの記事は完全一致ではないのでマッチしない（誤検知抑制）。"""
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "トヨタの新車種が発売"  # 「トヨタ自動車」ではない
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert result == []

    def test_no_match_returns_empty(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "ホンダの新型車が登場"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert result == []

    def test_suffix_stripped_for_match(self) -> None:
        """社名末尾の「株式会社」「ホールディングス」が正規化される。"""
        stocks = [_stock(1, "9984", "ソフトバンクグループ")]
        text = "ソフトバンクが投資先売却"  # 「グループ」を取り除いた「ソフトバンク」でマッチ
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 1

    def test_no_id_stock_skipped(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        stocks[0].id = None
        result = self.service.match(text="トヨタ自動車が決算", candidate_stocks=stocks)
        assert result == []

    def test_multiple_stocks_all_matched(self) -> None:
        stocks = [
            _stock(1, "7203", "トヨタ自動車"),
            _stock(2, "7267", "ホンダ"),
        ]
        text = "トヨタ自動車とホンダの決算が好調"
        result = self.service.match(text=text, candidate_stocks=stocks)
        assert len(result) == 2
        assert all(m.relevance_score == 1.0 for m in result)

    def test_empty_text_returns_empty(self) -> None:
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        result = self.service.match(text="", candidate_stocks=stocks)
        assert result == []

    def test_ticker_does_not_match_substring_of_other_number(self) -> None:
        """「72030」のような数字列の中に「7203」が出ても誤マッチしないこと。"""
        stocks = [_stock(1, "7203", "トヨタ自動車")]
        text = "出来高 72030 株"
        result = self.service.match(text=text, candidate_stocks=stocks)
        # 数字境界で囲んでいるので「72030」内の「7203」はマッチしない
        assert result == []
