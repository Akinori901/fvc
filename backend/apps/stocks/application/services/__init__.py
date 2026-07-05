"""Application services package.

既存の StockService / FinancialService を後方互換のためここからリエクスポート。
"""

from apps.core.exceptions import EntityNotFoundError

from ...domain.entities import FinancialEntity, StockEntity
from ...domain.repositories import FinancialRepository, StockRepository
from ..dto import CreateFinancialDTO, CreateStockDTO, UpdateStockDTO


class StockService:
    """銘柄管理サービス"""

    def __init__(self, stock_repo: StockRepository) -> None:
        self._stock_repo = stock_repo

    def list_stocks(self) -> list[StockEntity]:
        return self._stock_repo.list_all()

    def get_stock(self, code: str) -> StockEntity:
        stock = self._stock_repo.find_by_code(code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {code}")
        return stock

    def create_stock(self, dto: CreateStockDTO) -> StockEntity:
        entity = StockEntity(
            code=dto.code,
            name=dto.name,
            market=dto.market,
            sector=dto.sector,
        )
        return self._stock_repo.save(entity)

    def update_stock(self, code: str, dto: UpdateStockDTO) -> StockEntity:
        stock = self.get_stock(code)
        if dto.name is not None:
            stock.name = dto.name
        if dto.market is not None:
            stock.market = dto.market
        if dto.sector is not None:
            stock.sector = dto.sector
        return self._stock_repo.save(stock)

    def delete_stock(self, code: str) -> None:
        stock = self.get_stock(code)
        assert stock.id is not None
        self._stock_repo.delete(stock.id)


class FinancialService:
    """財務データ管理サービス"""

    def __init__(self, stock_repo: StockRepository, financial_repo: FinancialRepository) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo

    def list_financials(self, stock_code: str) -> list[FinancialEntity]:
        stock = self._stock_repo.find_by_code(stock_code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {stock_code}")
        assert stock.id is not None
        return self._financial_repo.find_by_stock_id(stock.id)

    def create_financial(self, dto: CreateFinancialDTO) -> FinancialEntity:
        stock = self._stock_repo.find_by_code(dto.stock_code)
        if stock is None:
            raise EntityNotFoundError(f"銘柄が見つかりません: {dto.stock_code}")
        assert stock.id is not None
        entity = FinancialEntity(
            stock_id=stock.id,
            fiscal_year=dto.fiscal_year,
            bps=dto.bps,
            eps=dto.eps,
            roe=dto.roe,
            net_assets=dto.net_assets,
            total_shares=dto.total_shares,
        )
        return self._financial_repo.save(entity)
