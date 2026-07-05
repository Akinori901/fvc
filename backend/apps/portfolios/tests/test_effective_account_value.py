from decimal import Decimal

from apps.portfolios.presentation.views import _effective_account_value


class TestEffectiveAccountValue:
    """口座評価額の補正ロジック（信用口座は損益のみ計上）"""

    def test_cash_account_returns_value_as_is(self) -> None:
        result = _effective_account_value(val=Decimal("5000000"), cost=Decimal("4000000"), is_margin=False)
        assert result == Decimal("5000000")

    def test_margin_account_returns_pnl_only(self) -> None:
        # 時価1000万、原価800万 → 損益 200万
        result = _effective_account_value(val=Decimal("10000000"), cost=Decimal("8000000"), is_margin=True)
        assert result == Decimal("2000000")

    def test_margin_account_with_loss_returns_negative(self) -> None:
        # 時価700万、原価800万 → 損益 -100万
        result = _effective_account_value(val=Decimal("7000000"), cost=Decimal("8000000"), is_margin=True)
        assert result == Decimal("-1000000")

    def test_margin_account_without_cost_returns_zero(self) -> None:
        # 信用口座で原価が欠損 → 0（過大評価を避ける）
        result = _effective_account_value(val=Decimal("10000000"), cost=None, is_margin=True)
        assert result == Decimal("0")

    def test_cash_account_without_cost_still_uses_value(self) -> None:
        # 現物口座は cost が無くても val をそのまま使う（保険・現金等）
        result = _effective_account_value(val=Decimal("3000000"), cost=None, is_margin=False)
        assert result == Decimal("3000000")

    def test_value_none_returns_zero(self) -> None:
        result = _effective_account_value(val=None, cost=None, is_margin=False)
        assert result == Decimal("0")

    def test_int_input_is_accepted(self) -> None:
        # 既存呼び出し側が int を渡すケース（snapshot.total_value_jpy が int の場合）
        result = _effective_account_value(val=5000000, cost=4000000, is_margin=True)
        assert result == Decimal("1000000")
