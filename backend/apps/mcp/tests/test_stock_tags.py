"""stock_tags 純関数のテスト（DB 不要）。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from apps.mcp.domain.stock_tags import compute_opportunity_tags, compute_risk_tags


def _result(
    *,
    long_balance: int | None = None,
    short_balance: int | None = None,
    avg_turnover_20d: Decimal | None = None,
    current_pbr: Decimal | None = None,
    fair_pbr: Decimal | None = None,
    fair_value: Decimal | None = Decimal("1000"),
    not_calculable_reason: str | None = None,
    progressive_dividend_years: int | None = None,
    price_position_52w: Decimal | None = None,
    evaluation_zone: str | None = None,
) -> MagicMock:
    r = MagicMock()
    r.long_balance = long_balance
    r.short_balance = short_balance
    r.avg_turnover_20d = avg_turnover_20d
    r.current_pbr = current_pbr
    r.fair_pbr = fair_pbr
    r.fair_value = fair_value
    r.not_calculable_reason = not_calculable_reason
    r.progressive_dividend_years = progressive_dividend_years
    r.price_position_52w = price_position_52w
    r.evaluation_zone = evaluation_zone
    return r


# ============================================================
# Risk tags
# ============================================================


class TestRiskHighMarginOverhang:
    def test_lights_when_short_zero_and_long_large(self) -> None:
        tags = compute_risk_tags(_result(long_balance=400_000, short_balance=0))
        assert any(t.tag == "risk_high_margin_overhang" and t.severity == "high" for t in tags)

    def test_lights_when_credit_ratio_above_5(self) -> None:
        tags = compute_risk_tags(_result(long_balance=600_000, short_balance=100_000))
        assert any(t.tag == "risk_high_margin_overhang" for t in tags)

    def test_no_tag_when_credit_ratio_below_5(self) -> None:
        tags = compute_risk_tags(_result(long_balance=100_000, short_balance=50_000))
        assert not any(t.tag == "risk_high_margin_overhang" for t in tags)

    def test_no_tag_when_short_zero_and_long_below_threshold(self) -> None:
        tags = compute_risk_tags(_result(long_balance=200_000, short_balance=0))
        assert not any(t.tag == "risk_high_margin_overhang" for t in tags)


class TestRiskLowLiquidity:
    def test_lights_when_turnover_below_100m(self) -> None:
        tags = compute_risk_tags(_result(avg_turnover_20d=Decimal("50000000"), fair_pbr=Decimal("1")))
        assert any(t.tag == "risk_low_liquidity" for t in tags)

    def test_no_tag_when_turnover_above_threshold(self) -> None:
        tags = compute_risk_tags(_result(avg_turnover_20d=Decimal("200000000"), fair_pbr=Decimal("1")))
        assert not any(t.tag == "risk_low_liquidity" for t in tags)


class TestRiskOvervaluedRelative:
    def test_lights_when_pbr_above_2x_fair(self) -> None:
        tags = compute_risk_tags(_result(current_pbr=Decimal("3.0"), fair_pbr=Decimal("1.0")))
        assert any(t.tag == "risk_overvalued_relative" for t in tags)

    def test_no_tag_when_pbr_within_2x(self) -> None:
        tags = compute_risk_tags(_result(current_pbr=Decimal("1.5"), fair_pbr=Decimal("1.0")))
        assert not any(t.tag == "risk_overvalued_relative" for t in tags)


class TestRiskNoFairValue:
    def test_lights_when_fair_value_none(self) -> None:
        tags = compute_risk_tags(_result(fair_value=None, not_calculable_reason="財務データ不足"))
        assert any(t.tag == "risk_no_fair_value" for t in tags)

    def test_no_tag_when_fair_value_present(self) -> None:
        tags = compute_risk_tags(_result(fair_value=Decimal("1000")))
        assert not any(t.tag == "risk_no_fair_value" for t in tags)


# ============================================================
# Opportunity tags
# ============================================================


class TestOpportunityConsecutiveDividendIncrease:
    def test_lights_when_progressive_5y(self) -> None:
        tags = compute_opportunity_tags(_result(progressive_dividend_years=5))
        assert any(t.tag == "opportunity_consecutive_dividend_increase" and t.severity == "high" for t in tags)

    def test_no_tag_when_progressive_4y(self) -> None:
        tags = compute_opportunity_tags(_result(progressive_dividend_years=4))
        assert not any(t.tag == "opportunity_consecutive_dividend_increase" for t in tags)


class TestOpportunityNear52wLow:
    def test_lights_when_position_5pct(self) -> None:
        tags = compute_opportunity_tags(_result(price_position_52w=Decimal("0.05")))
        assert any(t.tag == "opportunity_near_52w_low" for t in tags)

    def test_no_tag_when_position_20pct(self) -> None:
        tags = compute_opportunity_tags(_result(price_position_52w=Decimal("0.20")))
        assert not any(t.tag == "opportunity_near_52w_low" for t in tags)


class TestOpportunityValueZone:
    def test_lights_high_when_very_cheap(self) -> None:
        tags = compute_opportunity_tags(_result(evaluation_zone="very_cheap"))
        matched = [t for t in tags if t.tag == "opportunity_value_zone"]
        assert len(matched) == 1
        assert matched[0].severity == "high"

    def test_lights_medium_when_cheap(self) -> None:
        tags = compute_opportunity_tags(_result(evaluation_zone="cheap"))
        matched = [t for t in tags if t.tag == "opportunity_value_zone"]
        assert len(matched) == 1
        assert matched[0].severity == "medium"

    def test_no_tag_when_fair(self) -> None:
        tags = compute_opportunity_tags(_result(evaluation_zone="fair"))
        assert not any(t.tag == "opportunity_value_zone" for t in tags)


class TestOpportunityOversoldRsi:
    def test_lights_when_rsi_below_30(self) -> None:
        tags = compute_opportunity_tags(_result(), rsi_14=Decimal("25"))
        assert any(t.tag == "opportunity_oversold_rsi" for t in tags)

    def test_no_tag_when_rsi_50(self) -> None:
        tags = compute_opportunity_tags(_result(), rsi_14=Decimal("50"))
        assert not any(t.tag == "opportunity_oversold_rsi" for t in tags)

    def test_no_tag_when_rsi_none(self) -> None:
        tags = compute_opportunity_tags(_result(), rsi_14=None)
        assert not any(t.tag == "opportunity_oversold_rsi" for t in tags)
