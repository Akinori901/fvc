"""信用買残トレンドメトリクスのユニットテスト。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from apps.stocks.domain.entities import MarginBalanceEntity
from apps.stocks.domain.margin_trend_metrics import compute_margin_trend_metrics

if TYPE_CHECKING:
    from collections.abc import Sequence

_LATEST = date(2026, 7, 24)


def _make_margins(long_balances: Sequence[int | None], stock_id: int = 1) -> list[MarginBalanceEntity]:
    """long_balances を **新しい順** で受け取り、週次(7日間隔)の降順リストにする。"""
    return [
        MarginBalanceEntity(
            stock_id=stock_id,
            date=_LATEST - timedelta(weeks=i),
            long_balance=lb,
        )
        for i, lb in enumerate(long_balances)
    ]


class TestComputeMarginTrendMetrics:
    def test_decreasing_balance_is_detected(self) -> None:
        # 2ヶ月(≒9週)前 100,000 → 最新 80,000 で -20%
        margins = _make_margins([80_000] + [90_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_trend == "decreasing"
        assert result.long_balance_change_pct == Decimal("-20.00")

    def test_increasing_balance_is_detected(self) -> None:
        margins = _make_margins([120_000] + [110_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_trend == "increasing"
        assert result.long_balance_change_pct == Decimal("20.00")

    def test_small_change_is_flat(self) -> None:
        # +0.5% は閾値(1%)未満なので横ばい扱い
        margins = _make_margins([100_500] + [100_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_trend == "flat"

    def test_insufficient_history_returns_none(self) -> None:
        # 3週分しか無いのに 2ヶ月を要求 → 判定不能
        margins = _make_margins([80_000, 90_000, 100_000])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_change_pct is None
        assert result.long_balance_trend is None

    def test_single_point_returns_none(self) -> None:
        result = compute_margin_trend_metrics(_make_margins([80_000]), months=2)
        assert result.long_balance_change_pct is None

    def test_empty_input_returns_none(self) -> None:
        result = compute_margin_trend_metrics([], months=2)
        assert result.long_balance_change_pct is None

    def test_zero_months_returns_none(self) -> None:
        margins = _make_margins([80_000] + [90_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(margins, months=0)
        assert result.long_balance_change_pct is None

    def test_null_balances_are_skipped(self) -> None:
        # 途中に欠測があっても有効な2点が揃えば算出できる
        margins = _make_margins([80_000, None, None, None, None, None, None, None, None, 100_000])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_change_pct == Decimal("-20.00")

    def test_zero_baseline_returns_none(self) -> None:
        # 基準値が 0 なら変化率は計算できない（ゼロ除算回避）
        margins = _make_margins([80_000] + [90_000] * 8 + [0])
        result = compute_margin_trend_metrics(margins, months=2)
        assert result.long_balance_change_pct is None

    def test_unsorted_input_is_handled(self) -> None:
        # 呼び出し側の並びに依存せず date 降順に正規化される
        margins = _make_margins([80_000] + [90_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(list(reversed(margins)), months=2)
        assert result.long_balance_change_pct == Decimal("-20.00")

    def test_longer_period_uses_older_baseline(self) -> None:
        # 12ヶ月(≒52週) 指定時は 52週前を基準にする
        margins = _make_margins([50_000] + [80_000] * 51 + [100_000])
        result = compute_margin_trend_metrics(margins, months=12)
        assert result.long_balance_change_pct == Decimal("-50.00")
        assert result.long_balance_weeks_span == 52

    def test_twelve_months_with_only_two_months_history_returns_none(self) -> None:
        # 12ヶ月を要求したが 9週分しか無い → 手前のデータで代用せず判定不能
        margins = _make_margins([80_000] + [90_000] * 8 + [100_000])
        result = compute_margin_trend_metrics(margins, months=12)
        assert result.long_balance_change_pct is None
