"""銘柄詳細ページ用テクニカル指標計算ライブラリ。

全関数は古い順（ascending date）の close 終値リストを受け取り、
同じ長さの `list[Decimal | None]` を返す（計算不能な期間は None）。

純 Python 実装。numpy/pandas は使わない（Lambda パッケージサイズ削減のため）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from math import sqrt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.entities import PriceEntity


# ============================================================
# データクラス
# ============================================================


@dataclass
class IndicatorSeries:
    """日次の時系列ポイント。データ不足の指標は None。"""

    date: str
    close: Decimal
    ma_25: Decimal | None = None
    ma_75: Decimal | None = None
    ma_200: Decimal | None = None
    bb_upper: Decimal | None = None
    bb_middle: Decimal | None = None
    bb_lower: Decimal | None = None
    rsi_14: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_hist: Decimal | None = None
    stoch_k: Decimal | None = None
    stoch_d: Decimal | None = None
    atr_14: Decimal | None = None


@dataclass
class IndicatorLatest:
    """カード表示用の最新値 + 状態ラベル。"""

    # MA + 乖離率
    ma_25: Decimal | None = None
    ma_75: Decimal | None = None
    ma_200: Decimal | None = None
    ma_25_deviation_pct: Decimal | None = None
    ma_75_deviation_pct: Decimal | None = None
    ma_200_deviation_pct: Decimal | None = None
    # BB
    bb_upper: Decimal | None = None
    bb_middle: Decimal | None = None
    bb_lower: Decimal | None = None
    bb_position: Decimal | None = None  # %B = (close - lower) / (upper - lower)
    bb_signal: str | None = None  # 'above_upper' | 'below_lower' | 'inside'
    # RSI
    rsi_14: Decimal | None = None
    rsi_signal: str | None = None  # 'overbought' | 'oversold' | 'neutral'
    # MACD
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_hist: Decimal | None = None
    macd_cross: str | None = None  # 'golden' | 'dead' | 'none'
    # Stochastics
    stoch_k: Decimal | None = None
    stoch_d: Decimal | None = None
    stoch_signal: str | None = None  # 'overbought' | 'oversold' | 'neutral'
    # ATR
    atr_14: Decimal | None = None
    atr_pct: Decimal | None = None
    # Momentum
    momentum_25d_pct: Decimal | None = None
    momentum_signal: str | None = None  # 'strong_up' | 'up' | 'flat' | 'down' | 'strong_down'


@dataclass
class StockTechnicalIndicators:
    """銘柄テクニカル指標の集合（時系列 + 最新値）。"""

    series: list[IndicatorSeries] = field(default_factory=list)
    latest: IndicatorLatest | None = None
    data_points: int = 0
    insufficient_data: bool = False
    atr_approximation: str = "close_to_close"


# ============================================================
# 量子化用 Decimal 定数
# ============================================================

_Q2 = Decimal("0.01")
_Q4 = Decimal("0.0001")


def _q(value: float | Decimal, q: Decimal = _Q2) -> Decimal:
    """float / Decimal を指定精度の Decimal に量子化する。"""
    return Decimal(str(value)).quantize(q)


# ============================================================
# 移動平均（SMA / EMA）
# ============================================================


def compute_sma(closes: list[Decimal], period: int) -> list[Decimal | None]:
    """単純移動平均（SMA）を計算する。

    Args:
        closes: 古い順の終値リスト
        period: 移動平均期間

    Returns:
        closes と同じ長さのリスト。最初の (period-1) 個は None。
    """
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if period <= 0 or n < period:
        return result

    # 累積和で O(n) 計算
    floats = [float(c) for c in closes]
    running_sum = sum(floats[:period])
    result[period - 1] = _q(running_sum / period, _Q4)

    for i in range(period, n):
        running_sum += floats[i] - floats[i - period]
        result[i] = _q(running_sum / period, _Q4)

    return result


def compute_ema(closes: list[Decimal], period: int) -> list[Decimal | None]:
    """指数移動平均（EMA）を計算する。

    初期値は最初の period 日の SMA。以降は α = 2/(period+1) で更新。

    Args:
        closes: 古い順の終値リスト
        period: EMA 期間

    Returns:
        closes と同じ長さのリスト。最初の (period-1) 個は None。
    """
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if period <= 0 or n < period:
        return result

    floats = [float(c) for c in closes]
    alpha = 2.0 / (period + 1)

    # 初期値は SMA
    initial_sma = sum(floats[:period]) / period
    result[period - 1] = _q(initial_sma, _Q4)
    prev = initial_sma

    for i in range(period, n):
        ema = alpha * floats[i] + (1 - alpha) * prev
        result[i] = _q(ema, _Q4)
        prev = ema

    return result


# ============================================================
# RSI
# ============================================================


def compute_rsi(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """RSI (Wilder smoothing) を時系列で計算する。

    Args:
        closes: 古い順の終値リスト
        period: RSI 期間（デフォルト 14）

    Returns:
        closes と同じ長さのリスト。最初の period 個は None
        （計算には period+1 日必要のため）。
    """
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if period <= 0 or n < period + 1:
        return result

    floats = [float(c) for c in closes]
    deltas = [floats[i] - floats[i - 1] for i in range(1, n)]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]

    # 最初の period 個の平均で初期化
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi(g: float, loss_val: float) -> float:
        if loss_val == 0:
            return 100.0
        rs = g / loss_val
        return 100 - (100 / (1 + rs))

    # period 日目（インデックス period）で最初の RSI が確定
    result[period] = _q(_rsi(avg_gain, avg_loss), _Q2)

    # Wilder smoothing: avg = (prev * (period-1) + new) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result[i + 1] = _q(_rsi(avg_gain, avg_loss), _Q2)

    return result


# ============================================================
# Bollinger Bands
# ============================================================


def compute_bollinger_bands(
    closes: list[Decimal],
    period: int = 20,
    std_mult: Decimal = Decimal("2"),
) -> tuple[list[Decimal | None], list[Decimal | None], list[Decimal | None]]:
    """ボリンジャーバンド（上中下）を時系列で計算する。

    Returns:
        (upper, middle, lower) のタプル。各リストは closes と同じ長さ。
        最初の (period-1) 個は None。
    """
    n = len(closes)
    upper: list[Decimal | None] = [None] * n
    middle: list[Decimal | None] = [None] * n
    lower: list[Decimal | None] = [None] * n
    if period <= 0 or n < period:
        return upper, middle, lower

    floats = [float(c) for c in closes]
    mult = float(std_mult)

    for i in range(period - 1, n):
        window = floats[i - period + 1 : i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std = sqrt(variance)
        middle[i] = _q(mean, _Q4)
        upper[i] = _q(mean + mult * std, _Q4)
        lower[i] = _q(mean - mult * std, _Q4)

    return upper, middle, lower


# ============================================================
# MACD
# ============================================================


def compute_macd(
    closes: list[Decimal],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[list[Decimal | None], list[Decimal | None], list[Decimal | None]]:
    """MACD（macd, signal, histogram）を時系列で計算する。

    macd = EMA(closes, fast) - EMA(closes, slow)
    signal = EMA(macd_values, signal)
    histogram = macd - signal

    Returns:
        (macd, signal_line, histogram) のタプル。各リストは closes と同じ長さ。
        最初の (slow + signal - 2) 個程度は None。
    """
    n = len(closes)
    macd_list: list[Decimal | None] = [None] * n
    signal_list: list[Decimal | None] = [None] * n
    hist_list: list[Decimal | None] = [None] * n
    if n < slow:
        return macd_list, signal_list, hist_list

    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)

    # macd[i] = ema_fast[i] - ema_slow[i]（両方非 None のとき）
    macd_floats: list[float | None] = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            v = float(ema_fast[i]) - float(ema_slow[i])  # type: ignore[arg-type]
            macd_floats[i] = v
            macd_list[i] = _q(v, _Q4)

    # signal は macd 値（非 None 部分）に EMA を適用
    # 非 None になる最初のインデックス
    first_macd_idx = next((i for i, v in enumerate(macd_floats) if v is not None), None)
    if first_macd_idx is None:
        return macd_list, signal_list, hist_list

    macd_vals = [v for v in macd_floats[first_macd_idx:] if v is not None]
    if len(macd_vals) < signal:
        return macd_list, signal_list, hist_list

    alpha = 2.0 / (signal + 1)
    initial_sma = sum(macd_vals[:signal]) / signal
    # signal の最初の値は first_macd_idx + (signal - 1) に置く
    sig_start_idx = first_macd_idx + signal - 1
    signal_list[sig_start_idx] = _q(initial_sma, _Q4)
    hist_list[sig_start_idx] = _q(macd_vals[signal - 1] - initial_sma, _Q4)
    prev = initial_sma

    for j in range(signal, len(macd_vals)):
        sig_val = alpha * macd_vals[j] + (1 - alpha) * prev
        idx = first_macd_idx + j
        signal_list[idx] = _q(sig_val, _Q4)
        hist_list[idx] = _q(macd_vals[j] - sig_val, _Q4)
        prev = sig_val

    return macd_list, signal_list, hist_list


# ============================================================
# Stochastics (close-only 簡易版)
# ============================================================


def compute_stochastics(
    closes: list[Decimal],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[list[Decimal | None], list[Decimal | None]]:
    """ストキャスティクス（%K, %D）を close-only 近似で計算する。

    教科書版は high/low が必要だが、本実装では close のみで近似:
    %K = (close - min(close[-k:])) / (max - min) * 100
    %D = SMA(%K, d_period)

    Returns:
        (stoch_k, stoch_d) のタプル。各リストは closes と同じ長さ。
    """
    n = len(closes)
    k_list: list[Decimal | None] = [None] * n
    d_list: list[Decimal | None] = [None] * n
    if k_period <= 0 or n < k_period:
        return k_list, d_list

    floats = [float(c) for c in closes]

    for i in range(k_period - 1, n):
        window = floats[i - k_period + 1 : i + 1]
        hi = max(window)
        lo = min(window)
        if hi == lo:
            k_list[i] = Decimal("50.00")  # フラットなら中央
        else:
            k_val = (floats[i] - lo) / (hi - lo) * 100
            k_list[i] = _q(k_val, _Q2)

    # %D = SMA(%K, d_period)
    if n < k_period + d_period - 1:
        return k_list, d_list

    # k_list の非 None 値のみ抽出して SMA
    for i in range(k_period - 1 + d_period - 1, n):
        window_k = [k_list[j] for j in range(i - d_period + 1, i + 1)]
        if any(v is None for v in window_k):
            continue
        # window_k の全要素は非 None と確認済み
        total = 0.0
        for v in window_k:
            assert v is not None  # narrow
            total += float(v)
        d_list[i] = _q(total / d_period, _Q2)

    return k_list, d_list


# ============================================================
# ATR (close-to-close 近似)
# ============================================================


def compute_atr_close_approx(closes: list[Decimal], period: int = 14) -> list[Decimal | None]:
    """ATR を close-to-close 近似で計算する（Wilder smoothing）。

    教科書版 TR = max(high - low, |high - prev_close|, |low - prev_close|) だが、
    本実装では high/low データがないため:
    TR ≈ |close[i] - close[i-1]|
    ATR[i] = (ATR[i-1] * (period-1) + TR[i]) / period

    Returns:
        closes と同じ長さのリスト。最初の period 個は None。
    """
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if period <= 0 or n < period + 1:
        return result

    floats = [float(c) for c in closes]
    trs = [abs(floats[i] - floats[i - 1]) for i in range(1, n)]

    # 最初の period 個の平均で初期化
    avg_tr = sum(trs[:period]) / period
    result[period] = _q(avg_tr, _Q4)

    for i in range(period, len(trs)):
        avg_tr = (avg_tr * (period - 1) + trs[i]) / period
        result[i + 1] = _q(avg_tr, _Q4)

    return result


# ============================================================
# Momentum
# ============================================================


def compute_momentum_pct(closes: list[Decimal], period: int = 25) -> list[Decimal | None]:
    """N日変化率（%）を計算する。

    momentum[i] = (close[i] - close[i - period]) / close[i - period] * 100

    Returns:
        closes と同じ長さのリスト。最初の period 個は None。
    """
    n = len(closes)
    result: list[Decimal | None] = [None] * n
    if period <= 0 or n <= period:
        return result

    floats = [float(c) for c in closes]
    for i in range(period, n):
        prev = floats[i - period]
        if prev <= 0:
            continue
        momentum = (floats[i] - prev) / prev * 100
        result[i] = _q(momentum, _Q2)

    return result


# ============================================================
# 状態判定（カード用）
# ============================================================


def _rsi_signal(rsi: Decimal | None) -> str | None:
    if rsi is None:
        return None
    if rsi >= Decimal("70"):
        return "overbought"
    if rsi <= Decimal("30"):
        return "oversold"
    return "neutral"


def _bb_signal(close: Decimal, upper: Decimal | None, lower: Decimal | None) -> str | None:
    if upper is None or lower is None:
        return None
    if close > upper:
        return "above_upper"
    if close < lower:
        return "below_lower"
    return "inside"


def _bb_position(close: Decimal, upper: Decimal | None, lower: Decimal | None) -> Decimal | None:
    """%B = (close - lower) / (upper - lower)。"""
    if upper is None or lower is None or upper == lower:
        return None
    pos = (float(close) - float(lower)) / (float(upper) - float(lower))
    return _q(pos, _Q4)


def _stoch_signal(k: Decimal | None) -> str | None:
    if k is None:
        return None
    if k >= Decimal("80"):
        return "overbought"
    if k <= Decimal("20"):
        return "oversold"
    return "neutral"


def _macd_cross(hist_series: list[Decimal | None]) -> str | None:
    """直近2日のヒストグラムの符号変化でクロス判定。"""
    n = len(hist_series)
    if n < 2 or hist_series[-1] is None or hist_series[-2] is None:
        return None
    prev = hist_series[-2]
    curr = hist_series[-1]
    assert prev is not None and curr is not None  # narrow
    if prev <= 0 and curr > 0:
        return "golden"
    if prev >= 0 and curr < 0:
        return "dead"
    return "none"


def _momentum_signal(m: Decimal | None) -> str | None:
    if m is None:
        return None
    if m >= Decimal("20"):
        return "strong_up"
    if m >= Decimal("5"):
        return "up"
    if m >= Decimal("-5"):
        return "flat"
    if m >= Decimal("-20"):
        return "down"
    return "strong_down"


def _deviation_pct(close: Decimal, ma: Decimal | None) -> Decimal | None:
    if ma is None or ma == 0:
        return None
    return _q((float(close) - float(ma)) / float(ma) * 100, _Q2)


# ============================================================
# オーケストレーター
# ============================================================


def build_indicators(prices_desc: list[PriceEntity]) -> StockTechnicalIndicators:
    """株価データ（日付降順）から全テクニカル指標を計算する。

    Args:
        prices_desc: DjangoPriceRepository.find_by_stock_id() が返す降順リスト

    Returns:
        StockTechnicalIndicators（時系列 + 最新値 + メタ情報）
    """
    if not prices_desc:
        return StockTechnicalIndicators()

    # 古い順に並べ替え
    prices_asc = list(reversed(prices_desc))
    closes = [p.close_price for p in prices_asc]
    dates = [str(p.date) for p in prices_asc]
    n = len(closes)

    # 全指標を計算
    ma_25 = compute_sma(closes, 25)
    ma_75 = compute_sma(closes, 75)
    ma_200 = compute_sma(closes, 200)
    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(closes, 20, Decimal("2"))
    rsi_14 = compute_rsi(closes, 14)
    macd, macd_signal, macd_hist = compute_macd(closes, 12, 26, 9)
    stoch_k, stoch_d = compute_stochastics(closes, 14, 3)
    atr_14 = compute_atr_close_approx(closes, 14)
    momentum_25 = compute_momentum_pct(closes, 25)

    # 時系列ポイント構築
    series: list[IndicatorSeries] = []
    for i in range(n):
        series.append(
            IndicatorSeries(
                date=dates[i],
                close=closes[i],
                ma_25=ma_25[i],
                ma_75=ma_75[i],
                ma_200=ma_200[i],
                bb_upper=bb_upper[i],
                bb_middle=bb_middle[i],
                bb_lower=bb_lower[i],
                rsi_14=rsi_14[i],
                macd=macd[i],
                macd_signal=macd_signal[i],
                macd_hist=macd_hist[i],
                stoch_k=stoch_k[i],
                stoch_d=stoch_d[i],
                atr_14=atr_14[i],
            )
        )

    # 最新値
    latest_close = closes[-1]
    latest = IndicatorLatest(
        ma_25=ma_25[-1],
        ma_75=ma_75[-1],
        ma_200=ma_200[-1],
        ma_25_deviation_pct=_deviation_pct(latest_close, ma_25[-1]),
        ma_75_deviation_pct=_deviation_pct(latest_close, ma_75[-1]),
        ma_200_deviation_pct=_deviation_pct(latest_close, ma_200[-1]),
        bb_upper=bb_upper[-1],
        bb_middle=bb_middle[-1],
        bb_lower=bb_lower[-1],
        bb_position=_bb_position(latest_close, bb_upper[-1], bb_lower[-1]),
        bb_signal=_bb_signal(latest_close, bb_upper[-1], bb_lower[-1]),
        rsi_14=rsi_14[-1],
        rsi_signal=_rsi_signal(rsi_14[-1]),
        macd=macd[-1],
        macd_signal=macd_signal[-1],
        macd_hist=macd_hist[-1],
        macd_cross=_macd_cross(macd_hist),
        stoch_k=stoch_k[-1],
        stoch_d=stoch_d[-1],
        stoch_signal=_stoch_signal(stoch_k[-1]),
        atr_14=atr_14[-1],
        atr_pct=(
            _q(float(atr_14[-1]) / float(latest_close) * 100, _Q2)
            if atr_14[-1] is not None and latest_close > 0
            else None
        ),
        momentum_25d_pct=momentum_25[-1],
        momentum_signal=_momentum_signal(momentum_25[-1]),
    )

    return StockTechnicalIndicators(
        series=series,
        latest=latest,
        data_points=n,
        insufficient_data=n < 200,  # 200日MAが取れないと不十分扱い
        atr_approximation="close_to_close",
    )
