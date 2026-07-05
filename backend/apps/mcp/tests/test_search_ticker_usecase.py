"""search_ticker ツール UseCase の単体テスト（StockRepository をモック）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.mcp.application.usecases.tools.search_ticker_usecase import (
    SearchTickerToolUseCase,
)


def _stock(
    code: str,
    name: str,
    instrument_type: str = "stock",
    market: str = "東証グロース",
    market_type: str = "JP",
) -> MagicMock:
    s = MagicMock()
    s.code = code
    s.name = name
    s.instrument_type = instrument_type
    s.market = market
    s.market_type = market_type
    return s


class TestSearchTickerToolUseCase:
    def test_returns_matching_stocks(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = [
            _stock("5892", "ｙｕｔｏｒｉ"),
        ]

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        result = usecase.execute(query="yutori")

        assert result["count"] == 1
        assert result["query"] == "yutori"
        assert result["items"][0]["code"] == "5892"
        assert result["items"][0]["name"] == "ｙｕｔｏｒｉ"
        # Repository には NFKC 正規化済みの query が渡る
        call_kwargs = stock_repo.search_by_name.call_args
        assert call_kwargs.args[0] == "yutori"
        assert call_kwargs.kwargs["instrument_type"] is None  # "all" → None
        assert call_kwargs.kwargs["market_type"] is None
        assert call_kwargs.kwargs["limit"] == 10

    def test_zero_match_returns_empty_count(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        result = usecase.execute(query="zzzznotfound")

        assert result["count"] == 0
        assert result["items"] == []

    def test_normalizes_fullwidth_to_halfwidth(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="ｙｕｔｏｒｉ")  # 全角

        # NFKC 正規化で半角に変換されるはず
        assert stock_repo.search_by_name.call_args.args[0] == "yutori"

    def test_limit_clamped_to_hard_cap(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="トヨタ", limit=1000)

        assert stock_repo.search_by_name.call_args.kwargs["limit"] == 50

    def test_limit_minimum_clamped_to_1(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="トヨタ", limit=0)

        assert stock_repo.search_by_name.call_args.kwargs["limit"] == 1

    def test_instrument_type_filter_passed_through(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="日経", instrument_type="etf")

        assert stock_repo.search_by_name.call_args.kwargs["instrument_type"] == "etf"

    def test_instrument_type_all_passes_none_to_repo(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="トヨタ", instrument_type="all")

        assert stock_repo.search_by_name.call_args.kwargs["instrument_type"] is None

    def test_market_type_filter_passed_through(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = []

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        usecase.execute(query="AAPL", market_type="US")

        assert stock_repo.search_by_name.call_args.kwargs["market_type"] == "US"

    def test_empty_query_raises(self) -> None:
        usecase = SearchTickerToolUseCase(stock_repo=MagicMock())
        with pytest.raises(ValueError, match="query は必須"):
            usecase.execute(query="")

    def test_whitespace_only_query_raises(self) -> None:
        usecase = SearchTickerToolUseCase(stock_repo=MagicMock())
        with pytest.raises(ValueError, match="query は必須"):
            usecase.execute(query="   ")

    def test_invalid_instrument_type_raises(self) -> None:
        usecase = SearchTickerToolUseCase(stock_repo=MagicMock())
        with pytest.raises(ValueError, match="instrument_type"):
            usecase.execute(query="trade", instrument_type="bond")

    def test_invalid_market_type_raises(self) -> None:
        usecase = SearchTickerToolUseCase(stock_repo=MagicMock())
        with pytest.raises(ValueError, match="market_type"):
            usecase.execute(query="trade", market_type="HK")

    def test_response_items_shape(self) -> None:
        stock_repo = MagicMock()
        stock_repo.search_by_name.return_value = [
            _stock("7203", "トヨタ自動車", instrument_type="stock", market="東証プライム", market_type="JP"),
            _stock("9984", "ソフトバンクグループ", instrument_type="stock", market="東証プライム", market_type="JP"),
        ]

        usecase = SearchTickerToolUseCase(stock_repo=stock_repo)
        result = usecase.execute(query="トヨ")

        assert result["count"] == 2
        assert result["items"][0] == {
            "code": "7203",
            "name": "トヨタ自動車",
            "instrument_type": "stock",
            "market": "東証プライム",
            "market_type": "JP",
        }
