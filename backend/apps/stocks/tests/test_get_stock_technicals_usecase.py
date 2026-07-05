"""GetStockTechnicalsUseCase のユニットテスト（DBアクセスなし）。"""

from __future__ import annotations

import datetime
from decimal import Decimal

from apps.stocks.application.usecases.get_stock_technicals_usecase import (
    GetStockTechnicalsUseCase,
)
from apps.stocks.domain.entities import PriceEntity, StockEntity


class _FakeStockRepo:
    """テスト用 StockRepository fake。find_by_code のみ実装。"""

    def __init__(self, stocks: dict[str, StockEntity]) -> None:
        self._stocks = stocks

    def find_by_code(self, code: str) -> StockEntity | None:
        return self._stocks.get(code)

    # 他の抽象メソッドはテストで使わないが ABC を満たすため省略
    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        raise AttributeError(name)


class _FakePriceRepo:
    """テスト用 PriceRepository fake。find_by_stock_id のみ実装。"""

    def __init__(self, prices_by_stock: dict[int, list[PriceEntity]]) -> None:
        self._prices = prices_by_stock

    def find_by_stock_id(self, stock_id: int, limit: int = 100) -> list[PriceEntity]:
        prices = self._prices.get(stock_id, [])
        return prices[:limit]

    def __getattr__(self, name: str):  # type: ignore[no-untyped-def]
        raise AttributeError(name)


def _make_price_desc(n: int) -> list[PriceEntity]:
    """新しい順に n 件の価格データを生成する。"""
    base_date = datetime.date(2026, 5, 13)
    prices = []
    for i in range(n):
        d = base_date - datetime.timedelta(days=i)
        prices.append(
            PriceEntity(
                stock_id=1,
                date=str(d),
                close_price=Decimal(str(100 + (n - i))),  # 古い順に値段が上がる
                adj_factor=Decimal("1"),
            )
        )
    return prices


def _make_stock() -> StockEntity:
    return StockEntity(
        id=1,
        code="7203",
        name="Test",
        market_type="JP",
        market="prime",
        sector="トヨタ",
        is_active=True,
    )


class TestGetStockTechnicalsUseCase:
    def test_stock_not_found_returns_none(self) -> None:
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="9999")
        assert result is None

    def test_no_prices_returns_empty_indicators(self) -> None:
        stock = _make_stock()
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({"7203": stock}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({1: []}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="7203")
        assert result is not None
        assert result.series == []
        assert result.latest is None
        assert result.data_points == 0

    def test_full_data_returns_all_indicators(self) -> None:
        stock = _make_stock()
        prices = _make_price_desc(250)
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({"7203": stock}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({1: prices}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="7203", period="1y")
        assert result is not None
        assert result.data_points == 250
        assert result.insufficient_data is False
        assert result.latest is not None
        assert result.latest.ma_200 is not None
        # period=1y で末尾 252 日トリム → 250 日全部残る
        assert len(result.series) == 250

    def test_period_1m_trims_series(self) -> None:
        stock = _make_stock()
        prices = _make_price_desc(250)
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({"7203": stock}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({1: prices}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="7203", period="1m")
        assert result is not None
        # 1m は末尾 22 日にトリム
        assert len(result.series) == 22
        # data_points は計算に使った全データ件数
        assert result.data_points == 250

    def test_period_all_no_trim(self) -> None:
        stock = _make_stock()
        prices = _make_price_desc(100)
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({"7203": stock}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({1: prices}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="7203", period="all")
        assert result is not None
        assert len(result.series) == 100

    def test_insufficient_data_flag(self) -> None:
        stock = _make_stock()
        prices = _make_price_desc(100)
        usecase = GetStockTechnicalsUseCase(
            stock_repo=_FakeStockRepo({"7203": stock}),  # type: ignore[arg-type]
            price_repo=_FakePriceRepo({1: prices}),  # type: ignore[arg-type]
        )
        result = usecase.execute(code="7203", period="1y")
        assert result is not None
        assert result.insufficient_data is True
