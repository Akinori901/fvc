from decimal import Decimal

from apps.stocks.domain.entities import FinancialEntity


class TestFinancialEntity:
    def test_computed_roe_from_eps_and_bps(self) -> None:
        entity = FinancialEntity(
            stock_id=1,
            fiscal_year=2024,
            bps=Decimal("1000.00"),
            eps=Decimal("100.00"),
        )
        assert entity.computed_roe == Decimal("0.1")

    def test_computed_roe_returns_none_when_no_eps(self) -> None:
        entity = FinancialEntity(
            stock_id=1,
            fiscal_year=2024,
            bps=Decimal("1000.00"),
        )
        assert entity.computed_roe is None

    def test_computed_roe_ignores_stored_roe(self) -> None:
        """roe フィールドは J-Quants の EqAR（自己資本比率）であり ROE ではないため、
        eps がない場合は computed_roe は None を返す（フォールバックしない）。"""
        entity = FinancialEntity(
            stock_id=1,
            fiscal_year=2024,
            bps=Decimal("1000.00"),
            roe=Decimal("0.0800"),
        )
        assert entity.computed_roe is None
