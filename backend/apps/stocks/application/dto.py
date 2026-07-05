from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CreateStockDTO:
    code: str
    name: str
    market: str = ""
    sector: str = ""


@dataclass
class UpdateStockDTO:
    name: str | None = None
    market: str | None = None
    sector: str | None = None


@dataclass
class CreateFinancialDTO:
    stock_code: str
    fiscal_year: int
    bps: Decimal
    eps: Decimal | None = None
    roe: Decimal | None = None
    net_assets: int | None = None
    total_shares: int | None = None
