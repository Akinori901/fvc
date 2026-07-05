"""業界指標ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal


@dataclass
class IndustryMetricsEntity:
    """業界指標エンティティ。

    東証33業種ごとに、業界平均ROEのレンジ（下限〜上限）を保持する。
    保守シナリオの適正株価算出には min_roe を用いる。
    """

    sector: str
    min_roe: Decimal
    max_roe: Decimal
    note: str | None = None
    id: int | None = None
