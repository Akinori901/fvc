"""RecommendationUseCase の株価チャンク読み込みテスト（DB 不要・フェイク使用）。

全銘柄 × 252 日の株価を一度にメモリへ載せると Lambda のメモリを圧迫するため、
銘柄をチャンクに分けて読むよう変更した。分割しても結果が変わらないこと、
実際に分割して読んでいることを守るテスト。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.stocks.application.usecases import recommendation_usecase as ru
from apps.stocks.application.usecases.recommendation_usecase import RecommendationUseCase
from apps.stocks.domain.entities import PriceEntity, StockEntity

if TYPE_CHECKING:
    import pytest


def _stock(id_: int) -> StockEntity:
    return StockEntity(
        id=id_,
        code=str(1000 + id_),
        name=f"銘柄{id_}",
        market="プライム",
        market_type="JP",
        latest_price=Decimal("1000"),
    )


def _prices(stock_id: int, days: int = 252) -> list[PriceEntity]:
    """日付降順の株価。レンジ判定に載らないよう一定値にする。"""
    return [
        PriceEntity(
            stock_id=stock_id,
            date=f"2026-01-{(i % 28) + 1:02d}",
            close_price=Decimal("1000"),
            volume=1_000_000,
        )
        for i in range(days)
    ]


class _FakeStockRepo:
    def __init__(self, stocks: list[StockEntity]) -> None:
        self._stocks = stocks

    def find_by_market_type(self, market_type: str, active_only: bool = True) -> list[StockEntity]:  # noqa: ARG002
        return list(self._stocks)


class _FakeFinancialRepo:
    def find_all_latest(self) -> dict[int, Any]:
        return {}

    def find_all_recent(self, limit: int = 4) -> dict[int, list[Any]]:  # noqa: ARG002
        return {}


class _FakeDividendRepo:
    def find_all_annual_totals(self, stock_ids: list[int]) -> dict[int, Decimal]:  # noqa: ARG002
        return {}

    def find_all_by_stock_ids(self, stock_ids: list[int]) -> dict[int, list[Any]]:  # noqa: ARG002
        return {}


class _RecordingPriceRepo:
    """find_all_recent_prices の呼ばれ方を記録するフェイク。"""

    def __init__(self, stock_ids: list[int]) -> None:
        self._all = {sid: _prices(sid) for sid in stock_ids}
        self.calls: list[list[int] | None] = []

    def find_all_52w_high_low(self) -> dict[int, tuple[Decimal, Decimal]]:
        return {}

    def find_all_recent_prices(
        self, limit: int = 25, stock_ids: list[int] | None = None
    ) -> dict[int, list[PriceEntity]]:
        self.calls.append(list(stock_ids) if stock_ids is not None else None)
        target = self._all if stock_ids is None else {sid: self._all[sid] for sid in stock_ids if sid in self._all}
        return {sid: prices[:limit] for sid, prices in target.items()}


def _build(stock_count: int) -> tuple[RecommendationUseCase, _RecordingPriceRepo]:
    stocks = [_stock(i) for i in range(1, stock_count + 1)]
    price_repo = _RecordingPriceRepo([s.id for s in stocks if s.id is not None])
    usecase = RecommendationUseCase(
        stock_repo=_FakeStockRepo(stocks),  # type: ignore[arg-type]
        financial_repo=_FakeFinancialRepo(),  # type: ignore[arg-type]
        price_repo=price_repo,  # type: ignore[arg-type]
        dividend_repo=_FakeDividendRepo(),  # type: ignore[arg-type]
    )
    return usecase, price_repo


class TestChunkedPriceLoading:
    def test_prices_are_loaded_per_chunk(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """銘柄数がチャンクを超えると分割して読む。"""
        monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", 10)
        usecase, price_repo = _build(25)

        usecase.execute()

        assert len(price_repo.calls) == 3
        assert [len(c or []) for c in price_repo.calls] == [10, 10, 5]

    def test_no_call_loads_every_stock_at_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """全銘柄をまとめて読む呼び出しが残っていない。"""
        monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", 10)
        usecase, price_repo = _build(25)

        usecase.execute()

        # stock_ids=None（＝全銘柄一括）で呼ばれていないこと
        assert all(call is not None for call in price_repo.calls)
        assert all(len(call or []) <= 10 for call in price_repo.calls)

    def test_every_stock_is_requested_exactly_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """チャンク分割で銘柄の重複・取りこぼしが起きない。"""
        monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", 7)
        usecase, price_repo = _build(20)

        usecase.execute()

        requested = [sid for call in price_repo.calls for sid in (call or [])]
        assert sorted(requested) == list(range(1, 21))

    def test_chunk_size_larger_than_stocks_makes_single_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """銘柄数がチャンク未満なら 1 回で読む。"""
        monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", 500)
        usecase, price_repo = _build(3)

        usecase.execute()

        assert len(price_repo.calls) == 1

    def test_empty_stock_list_loads_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """対象銘柄が無ければ株価を読まない。"""
        monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", 10)
        usecase, price_repo = _build(0)

        result = usecase.execute()

        assert price_repo.calls == []
        assert result.long_term == []


class TestChunkingKeepsResultStable:
    def test_result_is_identical_across_chunk_sizes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """チャンクサイズを変えても抽出結果は変わらない。"""
        results = []
        for size in (3, 10, 500):
            monkeypatch.setattr(ru, "_STOCK_CHUNK_SIZE", size)
            usecase, _ = _build(25)
            dto = usecase.execute()
            results.append(
                (
                    [r.code for r in dto.long_term],
                    [r.code for r in dto.day_trade],
                    [r.code for r in dto.range_bound],
                )
            )

        assert results[0] == results[1] == results[2]


class TestChunkedHelper:
    def test_splits_into_even_chunks(self) -> None:
        assert [len(c) for c in ru._chunked([_stock(i) for i in range(1, 11)], 5)] == [5, 5]

    def test_last_chunk_holds_remainder(self) -> None:
        assert [len(c) for c in ru._chunked([_stock(i) for i in range(1, 8)], 3)] == [3, 3, 1]

    def test_empty_input_yields_nothing(self) -> None:
        assert list(ru._chunked([], 5)) == []
