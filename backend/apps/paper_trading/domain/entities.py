"""仮想売買ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class PaperTradeEntity:
    """売買記録エンティティ"""

    user_id: int
    stock_id: int
    trade_type: str  # "buy" | "sell"
    quantity: int
    price: Decimal
    total_amount: Decimal
    realized_profit: Decimal | None = None
    avg_cost_at_trade: Decimal | None = None
    memo: str = ""
    traded_at: datetime | None = None
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class PaperPositionEntity:
    """ポジション集計エンティティ"""

    user_id: int
    stock_id: int
    quantity: int
    total_cost: Decimal
    avg_cost_price: Decimal
    realized_profit_total: Decimal
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
