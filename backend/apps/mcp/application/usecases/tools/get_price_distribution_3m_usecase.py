"""3 ヶ月後株価分布予測ツール UseCase。

Historical Bootstrap で N 営業日後の株価分布を予測する。
過去 lookback_days 日の日次リターンを復元抽出してパス×simulation_runs 回試行。

Gordon Growth fair_value (ScreeningUseCase 由来) との比較で
prob_above_fair_value も同時計算する。

注意: 「過去リターンの繰り返しが続く」を前提とした統計モデル。
レジーム変化・構造変化は捉えられない。assumptions に明記する。
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.stocks.application.services.price_distribution_service import (
    BootstrapInput,
    compute_bootstrap_distribution,
)

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
    from apps.stocks.domain.repositories import PriceRepository, StockRepository


_DEFAULT_HORIZON_DAYS = 90
_DEFAULT_SIMULATION_RUNS = 10000
_DEFAULT_LOOKBACK_DAYS = 252
_SCREENING_GROWTH_RATE = Decimal("0.02")


class GetPriceDistribution3mToolUseCase:
    """指定銘柄の N 営業日後の株価分布を Historical Bootstrap で返す。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        price_repo: PriceRepository,
        screening_usecase: ScreeningUseCase,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._screening_usecase = screening_usecase

    def execute(
        self,
        *,
        code: str,
        horizon_days: int = _DEFAULT_HORIZON_DAYS,
        simulation_runs: int = _DEFAULT_SIMULATION_RUNS,
        lookback_days: int = _DEFAULT_LOOKBACK_DAYS,
        rng_seed: int | None = None,
    ) -> dict[str, Any]:
        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {code}")
        if stock.latest_price is None:
            raise ValueError(f"最新株価が未設定: {code}")

        # 過去 N 日の終値を取得（日付降順）
        prices_desc = self._price_repo.find_by_stock_id(stock.id, limit=lookback_days)
        historical_prices = [p.close_price for p in prices_desc]

        # fair_value を ScreeningUseCase から取得
        fair_value = self._fetch_fair_value(code)

        # Bootstrap 実行
        result = compute_bootstrap_distribution(
            BootstrapInput(
                current_price=stock.latest_price,
                historical_prices_desc=historical_prices,
                horizon_days=horizon_days,
                simulation_runs=simulation_runs,
                rng_seed=rng_seed,
            ),
            fair_value=fair_value,
        )

        if result.not_calculable_reason:
            return {
                "code": stock.code,
                "name": stock.name,
                "model": "bootstrap",
                "current_price": str(stock.latest_price),
                "fair_value": str(fair_value) if fair_value is not None else None,
                "horizon_days": horizon_days,
                "simulation_runs": simulation_runs,
                "expected_price": None,
                "percentiles": None,
                "prob_above_current": None,
                "prob_above_fair_value": None,
                "not_calculable_reason": result.not_calculable_reason,
                "assumptions": {
                    "lookback_days": lookback_days,
                    "historical_returns_count": result.historical_returns_count,
                    "as_of": datetime.date.today().isoformat(),
                },
            }

        return {
            "code": stock.code,
            "name": stock.name,
            "model": "bootstrap",
            "current_price": str(stock.latest_price),
            "fair_value": str(fair_value) if fair_value is not None else None,
            "horizon_days": horizon_days,
            "simulation_runs": simulation_runs,
            "expected_price": str(result.expected_price) if result.expected_price else None,
            "percentiles": {k: str(v) for k, v in result.percentiles.items()},
            "prob_above_current": (str(result.prob_above_current) if result.prob_above_current is not None else None),
            "prob_above_fair_value": (
                str(result.prob_above_fair_value) if result.prob_above_fair_value is not None else None
            ),
            "assumptions": {
                "lookback_days": lookback_days,
                "historical_returns_count": result.historical_returns_count,
                "as_of": datetime.date.today().isoformat(),
                "warning": "assumes_past_returns_continue",
            },
        }

    def _fetch_fair_value(self, code: str) -> Decimal | None:
        try:
            results = self._screening_usecase.execute(
                growth_rate=_SCREENING_GROWTH_RATE,
                code=code,
                include_inactive=True,
            )
        except Exception:  # noqa: BLE001
            return None
        if not results:
            return None
        return results[0].fair_value
