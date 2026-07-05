from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CalculateFairValueDTO:
    stock_code: str
    growth_rate: Decimal
    current_price: Decimal | None = None  # None の場合は最新株価を使用


@dataclass
class ReverseCalculateDTO:
    """市場織り込み成長率逆算 DTO"""

    stock_code: str
    current_price: Decimal | None = None  # None の場合は最新株価を使用
