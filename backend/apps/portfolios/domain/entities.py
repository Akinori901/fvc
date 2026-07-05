from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

# ============================================================
# 家族ポートフォリオ（新エンティティ）
# ============================================================


@dataclass
class FamilyMemberEntity:
    id: int | None
    user_id: int
    name: str
    role: str = "self"
    color_code: str = "#1976d2"
    display_order: int = 0
    include_in_family_total: bool = True


@dataclass
class PortfolioAccountEntity:
    id: int | None
    family_member_id: int
    institution: str
    institution_type: str
    asset_class: str
    trading_type: str = "spot"
    nickname: str = ""
    currency: str = "JPY"
    notes: str = ""
    is_active: bool = True
    expected_return_rate: Decimal | None = None
    family_member_name: str = ""
    margin_credit_type: str | None = None  # system_6m / general_6m / general_unlimited
    margin_interest_rate: Decimal | None = None  # 年率 (例: 0.0285)


@dataclass
class AccountHoldingEntity:
    id: int | None
    snapshot_id: int
    asset_name: str
    asset_type: str
    value_jpy: Decimal
    ticker_code: str = ""
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    cost_jpy: Decimal | None = None
    stock_id: int | None = None
    proxy_stock_id: int | None = None
    built_date: date | None = None  # 信用建玉日。未設定は snapshot_date を fallback


@dataclass
class AccountSnapshotEntity:
    id: int | None
    account_id: int
    snapshot_date: str
    total_value_jpy: Decimal
    total_cost_jpy: Decimal | None = None
    exchange_rate: Decimal | None = None
    notes: str = ""
    holdings: list[AccountHoldingEntity] = field(default_factory=list)


@dataclass
class WatchlistItemEntity:
    id: int | None
    user_id: int
    stock_id: int
    stock_code: str = ""
    stock_name: str = ""
    memo: str = ""
