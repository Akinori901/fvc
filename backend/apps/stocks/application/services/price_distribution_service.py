"""Historical Bootstrap による株価分布予測の純関数。

過去の日次リターンを復元抽出して N 営業日後の終値分布を生成する。
副作用なし。標準ライブラリ random のみで完結（numpy 不要）。

仮定: 「過去の日次リターン分布が将来も近似として続く」
- Fat-tail を自然に表現
- パラメータ推定不要
- 説明可能性が高い

警告: モンテカルロは「過去リターンの繰り返し」を前提とするため、
レジーム変化や構造変化を捉えられない。assumptions に明記する。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal

# 最小限の過去リターンサンプル数（これ未満なら計算不能とする）
_MIN_HISTORICAL_RETURNS = 30


@dataclass(frozen=True)
class BootstrapInput:
    """Bootstrap 計算の入力。"""

    current_price: Decimal
    historical_prices_desc: list[Decimal]  # 日付降順、先頭が最新
    horizon_days: int = 90  # 営業日
    simulation_runs: int = 10000
    rng_seed: int | None = None


@dataclass(frozen=True)
class BootstrapResult:
    """Bootstrap 計算の出力。"""

    expected_price: Decimal | None
    percentiles: dict[str, Decimal] = field(default_factory=dict)  # p10/p25/p50/p75/p90
    prob_above_current: Decimal | None = None
    prob_above_fair_value: Decimal | None = None
    historical_returns_count: int = 0
    not_calculable_reason: str | None = None


def compute_bootstrap_distribution(
    input_: BootstrapInput,
    *,
    fair_value: Decimal | None = None,
) -> BootstrapResult:
    """Bootstrap で N 日後の株価分布を計算する。

    Args:
        input_: 株価と過去価格、シミュレーション設定
        fair_value: 任意の比較基準価格 (例: Gordon Growth fair_value)

    Returns:
        BootstrapResult。データ不足時は not_calculable_reason を設定し他は None。
    """
    returns = _compute_daily_returns(input_.historical_prices_desc)
    if len(returns) < _MIN_HISTORICAL_RETURNS:
        return BootstrapResult(
            expected_price=None,
            historical_returns_count=len(returns),
            not_calculable_reason=f"historical_returns_insufficient (< {_MIN_HISTORICAL_RETURNS})",
        )

    rng = random.Random(input_.rng_seed)
    terminal_prices = _simulate(
        current_price=float(input_.current_price),
        returns=returns,
        horizon_days=input_.horizon_days,
        runs=input_.simulation_runs,
        rng=rng,
    )

    return _build_result(
        terminal_prices=terminal_prices,
        current_price=input_.current_price,
        fair_value=fair_value,
        returns_count=len(returns),
    )


def _compute_daily_returns(prices_desc: list[Decimal]) -> list[float]:
    """価格リスト（日付降順）から日次リターン（算術）を抽出する。"""
    if len(prices_desc) < 2:
        return []
    # 古い順に並び替えてから差分計算（説明しやすい順序）
    asc = list(reversed(prices_desc))
    out: list[float] = []
    for i in range(1, len(asc)):
        prev = float(asc[i - 1])
        curr = float(asc[i])
        if prev <= 0:
            continue
        out.append((curr - prev) / prev)
    return out


def _simulate(
    *,
    current_price: float,
    returns: list[float],
    horizon_days: int,
    runs: int,
    rng: random.Random,
) -> list[float]:
    """1 銘柄の Bootstrap パス × runs 回を実行。"""
    terminal: list[float] = []
    for _ in range(runs):
        price = current_price
        for _ in range(horizon_days):
            r = rng.choice(returns)
            price *= 1.0 + r
        terminal.append(price)
    terminal.sort()
    return terminal


def _build_result(
    *,
    terminal_prices: list[float],
    current_price: Decimal,
    fair_value: Decimal | None,
    returns_count: int,
) -> BootstrapResult:
    n = len(terminal_prices)
    expected = sum(terminal_prices) / n if n > 0 else None
    percentiles = {
        "p10": _percentile(terminal_prices, 0.10),
        "p25": _percentile(terminal_prices, 0.25),
        "p50": _percentile(terminal_prices, 0.50),
        "p75": _percentile(terminal_prices, 0.75),
        "p90": _percentile(terminal_prices, 0.90),
    }
    current_f = float(current_price)
    prob_above_current = _prob_above(terminal_prices, current_f)
    prob_above_fair = _prob_above(terminal_prices, float(fair_value)) if fair_value is not None else None

    return BootstrapResult(
        expected_price=_to_decimal(expected) if expected is not None else None,
        percentiles=percentiles,
        prob_above_current=_to_pct_decimal(prob_above_current),
        prob_above_fair_value=_to_pct_decimal(prob_above_fair) if prob_above_fair is not None else None,
        historical_returns_count=returns_count,
    )


def _percentile(sorted_values: list[float], q: float) -> Decimal:
    """ソート済みリストから q (0-1) のパーセンタイルを返す（最近傍法）。"""
    if not sorted_values:
        return Decimal("0")
    idx = int(q * (len(sorted_values) - 1))
    return _to_decimal(sorted_values[idx])


def _prob_above(sorted_values: list[float], threshold: float) -> float:
    """sorted_values のうち threshold を超える比率を返す。"""
    if not sorted_values:
        return 0.0
    count = sum(1 for v in sorted_values if v > threshold)
    return count / len(sorted_values)


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _to_pct_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(round(value, 4)))
