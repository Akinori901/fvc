"""price_distribution_service 純関数のテスト（DB 不要）。"""

from __future__ import annotations

from decimal import Decimal

from apps.stocks.application.services.price_distribution_service import (
    BootstrapInput,
    compute_bootstrap_distribution,
)


def _make_prices_desc(start: float, returns: list[float]) -> list[Decimal]:
    """start 価格から returns (古い順) を適用して価格列を作り、降順で返す。"""
    asc = [start]
    for r in returns:
        asc.append(asc[-1] * (1.0 + r))
    return [Decimal(str(p)) for p in reversed(asc)]


class TestComputeBootstrapDistribution:
    def test_returns_percentiles_for_simple_random_walk(self) -> None:
        # 30 日分の小さなランダムリターン (Bootstrap 計算可能な最小)
        returns = [0.01, -0.01] * 16  # 32 returns
        prices_desc = _make_prices_desc(1000.0, returns)

        result = compute_bootstrap_distribution(
            BootstrapInput(
                current_price=Decimal("1000"),
                historical_prices_desc=prices_desc,
                horizon_days=10,
                simulation_runs=500,
                rng_seed=42,
            )
        )

        assert result.not_calculable_reason is None
        assert result.expected_price is not None
        assert "p10" in result.percentiles
        assert "p50" in result.percentiles
        assert "p90" in result.percentiles
        # p10 < p50 < p90 が成立すること（確率分布の単調性）
        assert result.percentiles["p10"] <= result.percentiles["p50"] <= result.percentiles["p90"]
        assert result.prob_above_current is not None
        assert Decimal("0") <= result.prob_above_current <= Decimal("1")

    def test_insufficient_data_returns_reason(self) -> None:
        prices_desc = [Decimal("1000"), Decimal("999")]  # 1 return only
        result = compute_bootstrap_distribution(
            BootstrapInput(
                current_price=Decimal("1000"),
                historical_prices_desc=prices_desc,
                horizon_days=10,
                simulation_runs=100,
            )
        )
        assert result.not_calculable_reason is not None
        assert "insufficient" in result.not_calculable_reason
        assert result.expected_price is None

    def test_computes_prob_above_fair_value(self) -> None:
        # 上昇トレンド (常に +1%) のリターン
        returns = [0.01] * 50
        prices_desc = _make_prices_desc(1000.0, returns)

        result = compute_bootstrap_distribution(
            BootstrapInput(
                current_price=Decimal("1000"),
                historical_prices_desc=prices_desc,
                horizon_days=20,
                simulation_runs=500,
                rng_seed=42,
            ),
            fair_value=Decimal("1200"),
        )
        assert result.prob_above_fair_value is not None
        # 全リターンが +1% なので 20 日後の価格は 1000 * 1.01^20 ≈ 1220
        # → fair_value=1200 超過確率は高いはず
        assert result.prob_above_fair_value > Decimal("0.5")

    def test_rng_seed_makes_results_reproducible(self) -> None:
        returns = [0.01, -0.01, 0.005, -0.005] * 10
        prices_desc = _make_prices_desc(1000.0, returns)
        input_ = BootstrapInput(
            current_price=Decimal("1000"),
            historical_prices_desc=prices_desc,
            horizon_days=20,
            simulation_runs=200,
            rng_seed=123,
        )

        result1 = compute_bootstrap_distribution(input_)
        result2 = compute_bootstrap_distribution(input_)

        assert result1.expected_price == result2.expected_price
        assert result1.percentiles["p50"] == result2.percentiles["p50"]

    def test_empty_prices_returns_reason(self) -> None:
        result = compute_bootstrap_distribution(
            BootstrapInput(
                current_price=Decimal("1000"),
                historical_prices_desc=[],
                horizon_days=10,
                simulation_runs=100,
            )
        )
        assert result.not_calculable_reason is not None
        assert result.historical_returns_count == 0
