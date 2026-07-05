"""信用建玉の期限・累計金利・現引き必要資金の計算純関数。

副作用なし。リポジトリやモデルに依存しない。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

# 信用枠区分（PortfolioAccount.MarginCreditType と整合）
CREDIT_TYPE_SYSTEM_6M = "system_6m"
CREDIT_TYPE_GENERAL_6M = "general_6m"
CREDIT_TYPE_GENERAL_UNLIMITED = "general_unlimited"

_PERIOD_DAYS_6M = 180  # 暦日近似。営業日対応は別 PR
_EXPIRY_WARNING_DAYS = 30  # 期限警告閾値


@dataclass(frozen=True)
class MarginPositionInput:
    built_date: datetime.date | None
    snapshot_date: datetime.date  # built_date 未入力時の fallback
    credit_type: str | None  # system_6m / general_6m / general_unlimited
    interest_rate: Decimal | None  # 年率（例: 0.0285 = 2.85%）
    cost_jpy: Decimal | None
    as_of: datetime.date  # 現在日


@dataclass(frozen=True)
class MarginPositionOutput:
    effective_built_date: datetime.date  # built_date が None なら snapshot_date
    expiry_date: datetime.date | None  # general_unlimited は None
    days_to_expiry: int | None  # 期限までの日数（負数は期限切れ）
    days_held: int  # 建玉から as_of までの日数
    accrued_interest: Decimal | None  # 累計金利
    genbiki_cash_required: Decimal | None  # 現引き必要資金 (cost + 累計金利)
    warning_tags: list[str]  # ["expiry_30d_near"] / ["expired"] 等


def calculate(input_: MarginPositionInput) -> MarginPositionOutput:
    """信用建玉の期限・金利関連を一括算出する。"""
    effective_built_date = input_.built_date or input_.snapshot_date
    days_held = max((input_.as_of - effective_built_date).days, 0)

    expiry_date = _compute_expiry_date(effective_built_date, input_.credit_type)
    days_to_expiry = (expiry_date - input_.as_of).days if expiry_date is not None else None

    accrued_interest = _compute_accrued_interest(input_.cost_jpy, input_.interest_rate, days_held)
    genbiki_cash_required = (
        (input_.cost_jpy + accrued_interest) if (input_.cost_jpy is not None and accrued_interest is not None) else None
    )

    warning_tags = _build_warning_tags(days_to_expiry)

    return MarginPositionOutput(
        effective_built_date=effective_built_date,
        expiry_date=expiry_date,
        days_to_expiry=days_to_expiry,
        days_held=days_held,
        accrued_interest=accrued_interest,
        genbiki_cash_required=genbiki_cash_required,
        warning_tags=warning_tags,
    )


def _compute_expiry_date(built_date: datetime.date, credit_type: str | None) -> datetime.date | None:
    if credit_type in (CREDIT_TYPE_SYSTEM_6M, CREDIT_TYPE_GENERAL_6M):
        return built_date + datetime.timedelta(days=_PERIOD_DAYS_6M)
    return None


def _compute_accrued_interest(
    cost_jpy: Decimal | None,
    interest_rate: Decimal | None,
    days_held: int,
) -> Decimal | None:
    if cost_jpy is None or interest_rate is None or interest_rate <= 0:
        return None
    return (cost_jpy * interest_rate * Decimal(days_held) / Decimal(365)).quantize(Decimal("1"))


def _build_warning_tags(days_to_expiry: int | None) -> list[str]:
    if days_to_expiry is None:
        return []
    if days_to_expiry < 0:
        return ["expired"]
    if days_to_expiry <= _EXPIRY_WARNING_DAYS:
        return ["expiry_30d_near"]
    return []
