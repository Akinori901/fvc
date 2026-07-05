"""recommendation 用に追加したテクニカル指標のユニットテスト。"""

from __future__ import annotations

from decimal import Decimal

from apps.stocks.domain.entities import PriceEntity
from apps.stocks.domain.technical_metrics import (
    compute_range_metrics_1y,
    compute_volatility_20d,
)


def _make_prices(closes: list[float], stock_id: int = 1) -> list[PriceEntity]:
    """closes を **古い順** で受け取り、日付降順の PriceEntity リストにする。"""
    entities: list[PriceEntity] = []
    for i, close in enumerate(closes):
        # YYYY-MM-DD（古いほど 2020-01-01 寄り、新しいほど 2026-01-01 寄り）
        # 厳密な日付計算は不要、文字列順序だけ守れば良い
        date_str = f"2020-{(i // 30) % 12 + 1:02d}-{i % 30 + 1:02d}"
        entities.append(
            PriceEntity(
                stock_id=stock_id,
                date=date_str,
                close_price=Decimal(str(close)),
                volume=1_000_000,
            )
        )
    # 関数は降順前提
    entities.reverse()
    return entities


class TestComputeVolatility20d:
    def test_constant_prices_return_zero(self) -> None:
        # 価格が動かない → リターンの標準偏差は 0
        prices = _make_prices([1000.0] * 25)
        result = compute_volatility_20d(prices)
        assert result == Decimal("0.00")

    def test_alternating_prices_returns_nonzero(self) -> None:
        # 100 ↔ 110 を交互に → 日次リターンの標準偏差が一定値になる
        closes = []
        for i in range(25):
            closes.append(100.0 if i % 2 == 0 else 110.0)
        prices = _make_prices(closes)
        result = compute_volatility_20d(prices)
        assert result is not None
        # 検証: 0 ではない、かつ 1% 以上の動きはあるはず
        assert result > Decimal("4.0")  # 約4.7%程度になる想定

    def test_insufficient_data_returns_none(self) -> None:
        prices = _make_prices([100.0] * 10)
        assert compute_volatility_20d(prices) is None

    def test_exactly_21_days_works(self) -> None:
        prices = _make_prices([100.0] * 21)
        result = compute_volatility_20d(prices)
        assert result == Decimal("0.00")  # 一定値なので 0

    def test_zero_or_negative_close_returns_none(self) -> None:
        # 0 が混じると除算できないので None
        prices = _make_prices([100.0] * 25)
        # 中間に 0 を仕込む（日付降順なので reverse 済み、indexは新しい側から）
        prices[5] = PriceEntity(stock_id=1, date=prices[5].date, close_price=Decimal("0"), volume=1)
        assert compute_volatility_20d(prices) is None


class TestComputeRangeMetrics1y:
    def test_typical_range_market(self) -> None:
        # 1500-2000円のレンジで100営業日以上、ドリフトほぼゼロ
        closes = []
        for i in range(252):
            # サイン波風: 1750 ± 250
            offset = (i % 50) - 25  # -25〜+24
            closes.append(1750.0 + offset * 10)  # 1500〜1990
        prices = _make_prices(closes)
        result = compute_range_metrics_1y(prices)
        assert result is not None
        assert result.high >= Decimal("1980")
        assert result.low <= Decimal("1510")
        assert result.range_width >= Decimal("400")
        # 期初・期末 がほぼ同じ値（i=0 と i=251 で計算式同じはず）
        # i=0: offset = -25, close = 1500
        # i=251: offset = (251 % 50) - 25 = 1 - 25 = -24, close = 1510
        # drift = (1510 - 1500) / 1500 ≈ 0.0067
        assert abs(result.drift_pct) < Decimal("0.05")

    def test_uptrend_has_large_drift(self) -> None:
        # 1000円から2000円へ単調増加（明らかなトレンド、レンジではない）
        closes = [1000.0 + i * 4 for i in range(252)]
        prices = _make_prices(closes)
        result = compute_range_metrics_1y(prices)
        assert result is not None
        # drift +100% 程度
        assert result.drift_pct > Decimal("0.5")

    def test_insufficient_data_returns_none(self) -> None:
        prices = _make_prices([1000.0] * 50)  # 100 未満
        assert compute_range_metrics_1y(prices) is None

    def test_minimum_100_days_works(self) -> None:
        prices = _make_prices([1000.0 + (i % 10) * 100 for i in range(100)])
        result = compute_range_metrics_1y(prices)
        assert result is not None
        # 1000-1900 のレンジ
        assert result.high == Decimal("1900")
        assert result.low == Decimal("1000")

    def test_zero_low_returns_none(self) -> None:
        # close に 0 が混じる
        closes = [1000.0] * 200
        closes[150] = 0.0
        prices = _make_prices(closes)
        result = compute_range_metrics_1y(prices)
        assert result is None
