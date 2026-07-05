"""margin_calculator_service の純関数テスト（DB 不要）。"""

from __future__ import annotations

import datetime
from decimal import Decimal

from apps.portfolios.application.services.margin_calculator_service import (
    MarginPositionInput,
    calculate,
)


def _input(
    *,
    built_date: datetime.date | None = datetime.date(2026, 4, 15),
    snapshot_date: datetime.date = datetime.date(2026, 5, 1),
    credit_type: str | None = "system_6m",
    interest_rate: Decimal | None = Decimal("0.0285"),
    cost_jpy: Decimal | None = Decimal("235000"),
    as_of: datetime.date = datetime.date(2026, 5, 15),
) -> MarginPositionInput:
    return MarginPositionInput(
        built_date=built_date,
        snapshot_date=snapshot_date,
        credit_type=credit_type,
        interest_rate=interest_rate,
        cost_jpy=cost_jpy,
        as_of=as_of,
    )


class TestExpiryCalculation:
    def test_system_6m_has_180day_expiry(self) -> None:
        out = calculate(_input(credit_type="system_6m"))
        assert out.expiry_date == datetime.date(2026, 10, 12)  # 2026-04-15 + 180 days

    def test_general_6m_has_180day_expiry(self) -> None:
        out = calculate(_input(credit_type="general_6m"))
        assert out.expiry_date == datetime.date(2026, 10, 12)

    def test_general_unlimited_no_expiry(self) -> None:
        out = calculate(_input(credit_type="general_unlimited"))
        assert out.expiry_date is None
        assert out.days_to_expiry is None

    def test_none_credit_type_no_expiry(self) -> None:
        out = calculate(_input(credit_type=None))
        assert out.expiry_date is None


class TestBuiltDateFallback:
    def test_uses_built_date_when_provided(self) -> None:
        out = calculate(_input(built_date=datetime.date(2026, 4, 15)))
        assert out.effective_built_date == datetime.date(2026, 4, 15)

    def test_fallback_to_snapshot_date_when_built_date_none(self) -> None:
        out = calculate(_input(built_date=None, snapshot_date=datetime.date(2026, 5, 1)))
        assert out.effective_built_date == datetime.date(2026, 5, 1)


class TestAccruedInterest:
    def test_computes_accrued_interest(self) -> None:
        # 30 days held, 2.85% annual, cost 235,000
        # = 235000 * 0.0285 * 30 / 365 ≈ 550.48 → quantize to 550 (ROUND_HALF_EVEN)
        out = calculate(_input(as_of=datetime.date(2026, 5, 15)))
        assert out.accrued_interest is not None
        assert out.accrued_interest == Decimal("550")

    def test_null_when_interest_rate_missing(self) -> None:
        out = calculate(_input(interest_rate=None))
        assert out.accrued_interest is None

    def test_null_when_cost_missing(self) -> None:
        out = calculate(_input(cost_jpy=None))
        assert out.accrued_interest is None


class TestGenbikiCashRequired:
    def test_equals_cost_plus_interest(self) -> None:
        out = calculate(_input())
        assert out.genbiki_cash_required == Decimal("235550")  # 235000 + 550

    def test_null_when_components_missing(self) -> None:
        out = calculate(_input(cost_jpy=None))
        assert out.genbiki_cash_required is None


class TestWarningTags:
    def test_expiry_30d_near_when_within_30_days(self) -> None:
        # 期限 10/12、as_of 2026-09-15 → 期限まで 27 日
        out = calculate(_input(as_of=datetime.date(2026, 9, 15)))
        assert "expiry_30d_near" in out.warning_tags

    def test_no_warning_when_far_from_expiry(self) -> None:
        out = calculate(_input(as_of=datetime.date(2026, 5, 15)))
        assert out.warning_tags == []

    def test_expired_when_past_expiry(self) -> None:
        out = calculate(_input(as_of=datetime.date(2026, 11, 1)))
        assert "expired" in out.warning_tags

    def test_no_warning_for_unlimited(self) -> None:
        out = calculate(_input(credit_type="general_unlimited"))
        assert out.warning_tags == []
