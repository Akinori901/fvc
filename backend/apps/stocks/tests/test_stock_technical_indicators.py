"""stock_technical_indicators の純関数ユニットテスト（DBアクセスなし）。"""

from __future__ import annotations

import datetime
from decimal import Decimal

from apps.stocks.domain.entities import PriceEntity
from apps.stocks.domain.stock_technical_indicators import (
    build_indicators,
    compute_atr_close_approx,
    compute_bollinger_bands,
    compute_ema,
    compute_macd,
    compute_momentum_pct,
    compute_rsi,
    compute_sma,
    compute_stochastics,
)


def _D(x: str | int | float) -> Decimal:  # noqa: N802
    return Decimal(str(x))


def _make_price(day: int, close: float) -> PriceEntity:
    d = datetime.date(2026, 1, 1) + datetime.timedelta(days=day)
    return PriceEntity(
        stock_id=1,
        date=str(d),
        close_price=_D(close),
        adj_factor=_D("1"),
        pbr=None,
        volume=None,
    )


class TestComputeSma:
    def test_basic(self) -> None:
        closes = [_D("10"), _D("20"), _D("30")]
        result = compute_sma(closes, 2)
        assert result[0] is None
        assert result[1] == _D("15.0000")
        assert result[2] == _D("25.0000")

    def test_insufficient_data(self) -> None:
        result = compute_sma([_D("10"), _D("20")], 5)
        assert result == [None, None]

    def test_period_zero_returns_all_none(self) -> None:
        result = compute_sma([_D("10"), _D("20")], 0)
        assert result == [None, None]

    def test_constant_prices(self) -> None:
        closes = [_D("100")] * 30
        result = compute_sma(closes, 25)
        for v in result[:24]:
            assert v is None
        for v in result[24:]:
            assert v == _D("100.0000")


class TestComputeEma:
    def test_initial_sma_seed(self) -> None:
        closes = [_D("10"), _D("20"), _D("30")]
        result = compute_ema(closes, 2)
        # 初期 SMA: (10+20)/2 = 15
        assert result[1] == _D("15.0000")
        # 次は alpha=2/3、ema = 30*(2/3) + 15*(1/3) = 20+5 = 25
        assert result[2] == _D("25.0000")

    def test_insufficient_data(self) -> None:
        result = compute_ema([_D("10")], 5)
        assert result == [None]


class TestComputeRsi:
    def test_all_gains_returns_100(self) -> None:
        closes = [_D(str(i)) for i in range(1, 30)]
        result = compute_rsi(closes, 14)
        # 上昇のみ → avg_loss=0 → RSI=100
        assert result[-1] == _D("100.00")

    def test_insufficient_data(self) -> None:
        # period=14 なら最低 15 日必要
        closes = [_D(str(i)) for i in range(14)]
        result = compute_rsi(closes, 14)
        # 14 日では計算不可
        assert all(v is None for v in result)

    def test_alternating_prices(self) -> None:
        # 1, 2, 1, 2, ... の繰り返しは概ね 50% 付近に収束する
        closes = [_D(str(1 + i % 2)) for i in range(30)]
        result = compute_rsi(closes, 14)
        # RSI は計算される
        assert result[-1] is not None


class TestComputeBollingerBands:
    def test_constant_prices(self) -> None:
        # 一定価格なら std=0 → upper=middle=lower
        closes = [_D("100")] * 25
        upper, middle, lower = compute_bollinger_bands(closes, 20, _D("2"))
        assert upper[-1] == _D("100.0000")
        assert middle[-1] == _D("100.0000")
        assert lower[-1] == _D("100.0000")

    def test_upper_above_middle_above_lower(self) -> None:
        # ランダムっぽい価格
        closes = [_D(str(100 + (i * 7) % 11)) for i in range(25)]
        upper, middle, lower = compute_bollinger_bands(closes, 20, _D("2"))
        assert upper[-1] is not None
        assert middle[-1] is not None
        assert lower[-1] is not None
        assert upper[-1] >= middle[-1] >= lower[-1]

    def test_insufficient_data(self) -> None:
        closes = [_D("100")] * 10
        upper, middle, lower = compute_bollinger_bands(closes, 20)
        assert all(v is None for v in upper)


class TestComputeMacd:
    def test_constant_prices_gives_zero_macd(self) -> None:
        # 一定価格なら fast_ema = slow_ema → macd = 0
        closes = [_D("100")] * 50
        macd, signal, hist = compute_macd(closes, 12, 26, 9)
        # slow=26 + signal=9 - 1 で約 34 日目から確定
        assert macd[-1] == _D("0.0000")
        assert signal[-1] == _D("0.0000")
        assert hist[-1] == _D("0.0000")

    def test_insufficient_data(self) -> None:
        closes = [_D("100")] * 20
        macd, signal, hist = compute_macd(closes, 12, 26, 9)
        # slow=26 必要 → 全 None
        assert all(v is None for v in macd)


class TestComputeStochastics:
    def test_at_high_returns_100(self) -> None:
        # 最新が直近14日の最高値
        closes = [_D(str(i)) for i in range(1, 30)]
        k, d = compute_stochastics(closes, 14, 3)
        assert k[-1] == _D("100.00")

    def test_at_low_returns_0(self) -> None:
        closes = [_D(str(30 - i)) for i in range(30)]
        k, d = compute_stochastics(closes, 14, 3)
        assert k[-1] == _D("0.00")

    def test_constant_returns_50(self) -> None:
        # 一定価格 → hi=lo → 中央値 50
        closes = [_D("100")] * 20
        k, d = compute_stochastics(closes, 14, 3)
        assert k[-1] == _D("50.00")

    def test_insufficient_data(self) -> None:
        closes = [_D("100")] * 5
        k, d = compute_stochastics(closes, 14, 3)
        assert all(v is None for v in k)


class TestComputeAtr:
    def test_constant_returns_zero(self) -> None:
        closes = [_D("100")] * 20
        atr = compute_atr_close_approx(closes, 14)
        assert atr[-1] == _D("0.0000")

    def test_known_variation(self) -> None:
        # 1, 2, 1, 2, ... 変動 1 ずつ → ATR ≈ 1
        closes = [_D(str(1 + i % 2)) for i in range(20)]
        atr = compute_atr_close_approx(closes, 14)
        assert atr[-1] is not None
        assert abs(float(atr[-1]) - 1.0) < 0.1

    def test_insufficient_data(self) -> None:
        closes = [_D("100")] * 5
        atr = compute_atr_close_approx(closes, 14)
        assert all(v is None for v in atr)


class TestComputeMomentum:
    def test_50_percent_increase(self) -> None:
        # close[0]=100, close[25]=150 → momentum=50%
        closes = [_D("100")] * 25 + [_D("150")]
        result = compute_momentum_pct(closes, 25)
        assert result[-1] == _D("50.00")

    def test_decrease(self) -> None:
        closes = [_D("100")] * 25 + [_D("80")]
        result = compute_momentum_pct(closes, 25)
        assert result[-1] == _D("-20.00")

    def test_zero_prev_returns_none(self) -> None:
        closes = [_D("0")] * 25 + [_D("100")]
        result = compute_momentum_pct(closes, 25)
        assert result[-1] is None

    def test_insufficient_data(self) -> None:
        closes = [_D(str(i)) for i in range(20)]
        result = compute_momentum_pct(closes, 25)
        assert all(v is None for v in result)


class TestBuildIndicators:
    def test_empty_input(self) -> None:
        result = build_indicators([])
        assert result.series == []
        assert result.latest is None
        assert result.data_points == 0

    def test_insufficient_data_flag(self) -> None:
        # 100 日分 → 200日MA は取れず insufficient_data=True
        prices = [_make_price(i, 100.0 + i) for i in range(100)]
        prices.reverse()  # 降順入力
        result = build_indicators(prices)
        assert result.data_points == 100
        assert result.insufficient_data is True
        assert result.latest is not None
        assert result.latest.ma_200 is None
        # 25日MAは取れる
        assert result.latest.ma_25 is not None

    def test_full_data(self) -> None:
        # 250 日分 → 全指標が計算可能
        prices = [_make_price(i, 100.0 + (i % 7)) for i in range(250)]
        prices.reverse()
        result = build_indicators(prices)
        assert result.data_points == 250
        assert result.insufficient_data is False
        latest = result.latest
        assert latest is not None
        assert latest.ma_25 is not None
        assert latest.ma_75 is not None
        assert latest.ma_200 is not None
        assert latest.rsi_14 is not None
        assert latest.bb_upper is not None
        assert latest.macd is not None
        assert latest.stoch_k is not None
        assert latest.atr_14 is not None
        assert latest.momentum_25d_pct is not None

    def test_state_labels(self) -> None:
        # 上昇トレンドだと RSI=100。
        # momentum は (close[249] - close[224]) / close[224] * 100 = 25/324*100 ≈ 7.7% → "up"
        prices = [_make_price(i, 100.0 + i) for i in range(250)]
        prices.reverse()
        result = build_indicators(prices)
        latest = result.latest
        assert latest is not None
        assert latest.rsi_signal == "overbought"
        assert latest.momentum_signal == "up"

    def test_strong_up_momentum(self) -> None:
        # 25日で50%上昇 → strong_up
        prices = [_make_price(i, 100.0) for i in range(225)] + [
            _make_price(225 + i, 100.0 + (i + 1) * 2) for i in range(25)
        ]
        prices.reverse()
        result = build_indicators(prices)
        latest = result.latest
        assert latest is not None
        assert latest.momentum_signal == "strong_up"

    def test_atr_approximation_label(self) -> None:
        prices = [_make_price(i, 100.0) for i in range(30)]
        prices.reverse()
        result = build_indicators(prices)
        assert result.atr_approximation == "close_to_close"

    def test_series_length_matches_input(self) -> None:
        prices = [_make_price(i, 100.0 + i * 0.5) for i in range(50)]
        prices.reverse()
        result = build_indicators(prices)
        assert len(result.series) == 50
        # 最初の日は close のみ、ma25は None
        assert result.series[0].close == _D("100.0")
        assert result.series[0].ma_25 is None
        # 25日目以降の ma_25 は非 None
        assert result.series[24].ma_25 is not None


class TestStateJudgments:
    def test_rsi_overbought(self) -> None:
        # 単調増加 → 最後の RSI は 100
        prices = [_make_price(i, 100.0 + i) for i in range(30)]
        prices.reverse()
        result = build_indicators(prices)
        assert result.latest is not None
        assert result.latest.rsi_signal == "overbought"

    def test_rsi_oversold(self) -> None:
        # 単調減少 → RSI=0
        prices = [_make_price(i, 300.0 - i) for i in range(30)]
        prices.reverse()
        result = build_indicators(prices)
        assert result.latest is not None
        assert result.latest.rsi_14 == _D("0.00")
        assert result.latest.rsi_signal == "oversold"

    def test_momentum_signal_flat(self) -> None:
        # 一定価格 → momentum=0% → flat
        prices = [_make_price(i, 100.0) for i in range(30)]
        prices.reverse()
        result = build_indicators(prices)
        assert result.latest is not None
        assert result.latest.momentum_signal == "flat"
