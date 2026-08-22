"""FinancialSyncService のバルク/逐次分岐テスト（DB 不要・フェイク使用）。

全銘柄を1銘柄ずつ逐次取得すると銘柄数×sleep で Lambda がタイムアウトするため、
sync_prices と同型のバルク分岐を sync() に追加した。その分岐条件を守るテスト。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from apps.stocks.application.services.financial_sync_service import FinancialSyncService
from apps.stocks.domain.entities import FinancialEntity, StockEntity
from apps.stocks.domain.repositories import MarketFinancialData

if TYPE_CHECKING:
    from datetime import date


class _FakeStockRepo:
    def __init__(self, stocks: list[StockEntity]) -> None:
        self._stocks = stocks

    def find_by_market_type(self, market_type: str) -> list[StockEntity]:
        return [s for s in self._stocks if s.market_type == market_type]

    def find_by_code(self, code: str) -> StockEntity | None:
        return next((s for s in self._stocks if s.code == code), None)


class _FakeFinancialRepo:
    def __init__(self) -> None:
        self.saved: list[FinancialEntity] = []
        self.bulk_saved: list[FinancialEntity] = []

    def save(self, entity: FinancialEntity) -> None:
        self.saved.append(entity)

    def bulk_save(self, entities: list[FinancialEntity]) -> None:
        self.bulk_saved.extend(entities)


class _FakeProvider:
    """bulk 対応/非対応を切り替えられるフェイクプロバイダー。"""

    def __init__(self, *, supports_bulk: bool) -> None:
        self._supports_bulk = supports_bulk
        self.bulk_calls = 0
        self.per_stock_calls = 0

    def supports_bulk_fetch(self) -> bool:
        return self._supports_bulk

    def fetch_all_financials(self, from_date: date, to_date: date) -> list[MarketFinancialData]:
        self.bulk_calls += 1
        return [
            MarketFinancialData(code="7203", fiscal_year=2025, bps=Decimal("2000"), eps=Decimal("200")),
        ]

    def fetch_financials(self, code: str, fiscal_year: int | None = None) -> list[MarketFinancialData]:
        self.per_stock_calls += 1
        return [MarketFinancialData(code=code, fiscal_year=2025, bps=Decimal("1500"))]


def _stock(code: str, market_type: str = "JP", stock_id: int = 1) -> StockEntity:
    return StockEntity(code=code, name=f"stock-{code}", market_type=market_type, id=stock_id)


class TestSyncBulkBranch:
    def test_bulk_provider_no_codes_uses_bulk(self) -> None:
        """バルク対応・コード/年度指定なし → バルク経路（1銘柄ずつ叩かない）。"""
        stock_repo = _FakeStockRepo([_stock("7203")])
        fin_repo = _FakeFinancialRepo()
        provider = _FakeProvider(supports_bulk=True)
        svc = FinancialSyncService(stock_repo, fin_repo)  # type: ignore[arg-type]

        success, errors, _ = svc.sync(provider, "JP")  # type: ignore[arg-type]

        assert provider.bulk_calls == 1
        assert provider.per_stock_calls == 0
        assert success == 1
        assert errors == 0
        assert len(fin_repo.saved) == 1  # バルクは save() を使う

    def test_codes_specified_uses_per_stock(self) -> None:
        """コード指定あり → 逐次経路（バルクを使わない）。"""
        stock_repo = _FakeStockRepo([_stock("7203", stock_id=1), _stock("6758", stock_id=2)])
        fin_repo = _FakeFinancialRepo()
        provider = _FakeProvider(supports_bulk=True)
        svc = FinancialSyncService(stock_repo, fin_repo)  # type: ignore[arg-type]

        svc.sync(provider, "JP", codes=["7203"])  # type: ignore[arg-type]

        assert provider.bulk_calls == 0
        assert provider.per_stock_calls == 1  # 指定した1銘柄のみ

    def test_fiscal_year_specified_uses_per_stock(self) -> None:
        """年度指定あり → 逐次経路（バルクは年度指定に非対応のため）。"""
        stock_repo = _FakeStockRepo([_stock("7203")])
        fin_repo = _FakeFinancialRepo()
        provider = _FakeProvider(supports_bulk=True)
        svc = FinancialSyncService(stock_repo, fin_repo)  # type: ignore[arg-type]

        svc.sync(provider, "JP", fiscal_year=2024)  # type: ignore[arg-type]

        assert provider.bulk_calls == 0
        assert provider.per_stock_calls == 1

    def test_non_bulk_provider_uses_per_stock(self) -> None:
        """バルク非対応プロバイダー（US/yfinance 等）→ 逐次経路。"""
        stock_repo = _FakeStockRepo([_stock("AAPL", market_type="US")])
        fin_repo = _FakeFinancialRepo()
        provider = _FakeProvider(supports_bulk=False)
        svc = FinancialSyncService(stock_repo, fin_repo)  # type: ignore[arg-type]

        svc.sync(provider, "US")  # type: ignore[arg-type]

        assert provider.bulk_calls == 0
        assert provider.per_stock_calls == 1
