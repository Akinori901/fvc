"""仮想売買DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class ExecuteTradeDTO:
    user_id: int
    stock_code: str
    trade_type: str  # "buy" | "sell"
    quantity: int
    memo: str = ""


@dataclass
class TradeResultDTO:
    trade_id: int
    trade_type: str
    stock_code: str
    stock_name: str
    quantity: int
    price: Decimal
    total_amount: Decimal
    realized_profit: Decimal | None
    avg_cost_price: Decimal
    position_quantity: int
    position_total_cost: Decimal


@dataclass
class PositionDTO:
    stock_code: str
    stock_name: str
    quantity: int
    avg_cost_price: Decimal
    total_cost: Decimal
    latest_price: Decimal | None
    unrealized_profit: Decimal | None
    unrealized_profit_pct: Decimal | None
    realized_profit_total: Decimal


@dataclass
class PositionListDTO:
    positions: list[PositionDTO]
    total_investment: Decimal
    total_unrealized_profit: Decimal
    total_realized_profit: Decimal
    position_count: int


@dataclass
class TradeHistoryDTO:
    id: int
    stock_code: str
    stock_name: str
    trade_type: str
    quantity: int
    price: Decimal
    total_amount: Decimal
    realized_profit: Decimal | None
    memo: str
    traded_at: datetime
