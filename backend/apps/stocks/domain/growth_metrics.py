"""業績成長指標の計算ロジック。"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import FinancialEntity


@dataclass
class GrowthMetrics:
    """業績成長指標。データ不足の場合は各フィールドが None になる。"""

    eps_growth_yoy: Decimal | None  # EPS 前年比成長率
    eps_cagr_3y: Decimal | None  # EPS 3年 CAGR
    roe_trend: str | None  # "improving" / "declining" / "stable"
    revenue_growth_yoy: Decimal | None
    op_income_growth_yoy: Decimal | None


def compute_growth_metrics(financials: list[FinancialEntity]) -> GrowthMetrics:
    """成長指標を計算する。

    Args:
        financials: 年度降順 (最新が先頭) の財務データリスト。最低2件必要。
    """
    if not financials:
        return GrowthMetrics(None, None, None, None, None)

    latest = financials[0]

    # --- EPS 前年比成長率 ---
    eps_growth_yoy: Decimal | None = None
    if len(financials) >= 2:
        prev = financials[1]
        e0 = latest.eps
        e1 = prev.eps
        if e0 is not None and e1 is not None and e1 != 0:
            eps_growth_yoy = (e0 - e1) / abs(e1)

    # --- EPS 3年 CAGR ---
    eps_cagr_3y: Decimal | None = None
    if len(financials) >= 4:
        base = financials[3]
        e0 = latest.eps
        e_base = base.eps
        if e0 is not None and e_base is not None and e_base > 0 and e0 > 0:
            with contextlib.suppress(Exception):
                eps_cagr_3y = (e0 / e_base) ** (Decimal("1") / Decimal("3")) - Decimal("1")

    # --- ROE トレンド (直近3年の computed_roe の変化方向) ---
    roe_trend: str | None = None
    if len(financials) >= 2:
        roes = [f.computed_roe for f in financials[:3] if f.computed_roe is not None]
        if len(roes) >= 2:
            diff = roes[0] - roes[-1]
            if diff > Decimal("0.01"):
                roe_trend = "improving"
            elif diff < Decimal("-0.01"):
                roe_trend = "declining"
            else:
                roe_trend = "stable"

    # --- 売上高前年比成長率 ---
    revenue_growth_yoy: Decimal | None = None
    if len(financials) >= 2:
        r0 = latest.revenue
        r1 = financials[1].revenue
        if r0 is not None and r1 is not None and r1 != 0:
            revenue_growth_yoy = Decimal(r0 - r1) / abs(Decimal(r1))

    # --- 営業利益前年比成長率 ---
    op_income_growth_yoy: Decimal | None = None
    if len(financials) >= 2:
        o0 = latest.operating_income
        o1 = financials[1].operating_income
        if o0 is not None and o1 is not None and o1 != 0:
            op_income_growth_yoy = Decimal(o0 - o1) / abs(Decimal(o1))

    return GrowthMetrics(
        eps_growth_yoy=eps_growth_yoy,
        eps_cagr_3y=eps_cagr_3y,
        roe_trend=roe_trend,
        revenue_growth_yoy=revenue_growth_yoy,
        op_income_growth_yoy=op_income_growth_yoy,
    )
