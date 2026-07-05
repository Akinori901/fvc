from decimal import Decimal

from apps.valuations.domain.entities import FairValueCalculation


class TestFairValueCalculation:
    def test_fair_pbr_with_10_percent_growth(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.10"),
            bps=Decimal("1000.00"),
            current_price=Decimal("1500.00"),
            roe=Decimal("0.12"),
            cost_of_capital=Decimal("0.11"),
        )
        # PBR = (ROE - g) / (r - g) = (0.12 - 0.10) / (0.11 - 0.10) = 2.0
        assert calc.fair_pbr == Decimal("2.0")

    def test_fair_value_calculation(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.10"),
            bps=Decimal("1000.00"),
            current_price=Decimal("1500.00"),
            roe=Decimal("0.12"),
            cost_of_capital=Decimal("0.11"),
        )
        # fair_value = BPS(1000) * PBR(2.0) = 2000.00
        assert calc.fair_value == Decimal("2000.00")

    def test_is_undervalued_when_price_below_fair_value(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.10"),
            bps=Decimal("1000.00"),
            current_price=Decimal("1500.00"),
            roe=Decimal("0.12"),
            cost_of_capital=Decimal("0.11"),
        )
        # fair_value=2000 > current_price=1500 → 割安
        assert calc.is_undervalued is True

    def test_is_not_undervalued_when_price_above_fair_value(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.05"),
            bps=Decimal("1000.00"),
            current_price=Decimal("2000.00"),
            roe=Decimal("0.14"),
            cost_of_capital=Decimal("0.11"),
        )
        # PBR = (0.14 - 0.05) / (0.11 - 0.05) = 1.5, fair_value = 1500 < current_price=2000 → 割高
        assert calc.is_undervalued is False

    def test_discount_rate_positive_means_undervalued(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.10"),
            bps=Decimal("1000.00"),
            current_price=Decimal("1500.00"),
            roe=Decimal("0.12"),
            cost_of_capital=Decimal("0.11"),
        )
        # discount_rate = (2000-1500)/2000 = 0.25
        assert calc.discount_rate == Decimal("0.2500")

    def test_zero_growth_gives_pbr_one(self) -> None:
        calc = FairValueCalculation(
            growth_rate=Decimal("0.00"),
            bps=Decimal("1000.00"),
            current_price=Decimal("1000.00"),
            roe=Decimal("0.11"),
            cost_of_capital=Decimal("0.11"),
        )
        # PBR = (0.11 - 0) / (0.11 - 0) = 1.0
        assert calc.fair_pbr == Decimal("1")
        assert calc.fair_value == Decimal("1000.00")
