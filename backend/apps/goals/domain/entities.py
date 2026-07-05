"""目標管理ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class FinancialGoalEntity:
    """金融目標エンティティ。

    scope_type:
      - "family": 家族合計（include_in_family_total=True の全メンバー）
      - "members": 指定メンバーの組み合わせ（member_ids で指定）
    """

    user_id: int
    name: str
    target_value_jpy: Decimal
    target_date: str  # YYYY-MM-DD（月初固定）
    scope_type: str  # "family" | "members"
    member_ids: list[int] = field(default_factory=list)
    is_active: bool = True
    display_order: int = 0
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
