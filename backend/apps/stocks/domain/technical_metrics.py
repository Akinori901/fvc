"""52週高値効果テクニカル指標の計算ロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from .stock_technical_indicators import compute_macd, compute_rsi, compute_sma

if TYPE_CHECKING:
    from .entities import PriceEntity

# 買い時シグナル判定のパラメータ
_RECENT_WINDOW = 5  # クロス/反発は直近5営業日以内に発生
_BELOW_DAYS = 20  # クロス直前に20営業日以上、下側にあったこと（MA/株価ブレイク系のみ）
_BUY_SIGNAL_MIN_LEN = 100  # 75日MA + 20日下 + 5日窓 に足る最低日数。未満は判定対象外


@dataclass
class TechnicalMetrics:
    """テクニカル指標。データ不足の場合は各フィールドが None になる。"""

    price_position_52w: Decimal | None  # 52週レンジ内の位置 (0.0〜1.0)
    near_52w_high: bool | None  # 52週高値近接フラグ (5%以内)
    distance_from_52w_high: Decimal | None  # 52週高値からの乖離率
    volume_ratio_20d: Decimal | None  # 出来高比率 (5日平均/20日平均)
    ma_25_deviation: Decimal | None  # 25日移動平均乖離率
    momentum_signal: str | None  # "strong_buy" / "buy" / "neutral" / "caution" / "sell"
    avg_turnover_20d: Decimal | None  # 売買代金20日平均（円）
    # --- 買い時シグナル（データ不足時は False = 非該当） ---
    ma_golden_cross: bool = False  # 25日線が75日線を上抜け（20日下→直近5日）
    price_cross_ma25: bool = False  # 終値が25日線を上抜け（20日下→直近5日）
    price_cross_ma75: bool = False  # 終値が75日線を上抜け（20日下→直近5日）
    macd_golden_cross: bool = False  # MACDがシグナル線を上抜け（直近5日）
    rsi_rebound: bool = False  # RSI(14)が30以下から30を上抜け（直近5日）
    pullback_buy: bool = False  # 上昇トレンド中の押し目買い（直近5日）


def _compute_momentum_signal(
    price_position_52w: Decimal | None,
    volume_ratio_20d: Decimal | None,
    ma_25_deviation: Decimal | None,
) -> str | None:
    """モメンタムシグナルを判定する。"""
    if price_position_52w is None:
        return None

    has_volume_confirmation = volume_ratio_20d is not None and volume_ratio_20d > Decimal("1.0")
    has_strong_volume = volume_ratio_20d is not None and volume_ratio_20d > Decimal("1.5")
    above_ma25 = ma_25_deviation is not None and ma_25_deviation > Decimal("0")

    if price_position_52w >= Decimal("0.95") and has_strong_volume:
        return "strong_buy"
    if price_position_52w >= Decimal("0.80") and (has_volume_confirmation or above_ma25):
        return "buy"
    if price_position_52w >= Decimal("0.50"):
        return "neutral"
    if price_position_52w >= Decimal("0.30"):
        return "caution"
    return "sell"


def _crossed_up(
    a: list[Decimal | None],
    b: list[Decimal | None],
    *,
    require_below: bool,
) -> bool:
    """系列 a が系列 b を直近5営業日以内に下から上へ抜けたか判定する。

    require_below=True の場合、クロス直前の20営業日以上 a < b が継続していたことも要求する
    （MA/株価ブレイク系の「しばらく下にあった後の上抜け」）。
    a / b は古い順（末尾が最新）で、要素は Decimal | None。
    """
    n = len(a)
    cross_idx: int | None = None
    for i in range(max(1, n - _RECENT_WINDOW), n):
        pa, pb, ca, cb = a[i - 1], b[i - 1], a[i], b[i]
        if pa is None or pb is None or ca is None or cb is None:
            continue
        if pa <= pb and ca > cb:
            cross_idx = i  # 最も新しい上抜け点を採用
    if cross_idx is None:
        return False
    if not require_below:
        return True
    start = cross_idx - _BELOW_DAYS
    if start < 0:
        return False
    for j in range(start, cross_idx):
        aj, bj = a[j], b[j]
        if aj is None or bj is None or aj >= bj:
            return False
    return True


def _rebound_up(series: list[Decimal | None], threshold: Decimal) -> bool:
    """series が直近5営業日以内に threshold を下から上へ抜けたか（RSI反発用）。"""
    n = len(series)
    for i in range(max(1, n - _RECENT_WINDOW), n):
        prev, curr = series[i - 1], series[i]
        if prev is None or curr is None:
            continue
        if prev <= threshold and curr > threshold:
            return True
    return False


def _compute_buy_signals(
    recent_prices: list[PriceEntity],
    *,
    need_ma: bool,
    need_macd: bool,
    need_rsi: bool,
) -> dict[str, bool]:
    """買い時シグナルを判定する。recent_prices は日付降順（先頭が最新）。

    データが100営業日未満の銘柄、または該当フィルタが不要な系列は計算せず False を返す。
    """
    result = {
        "ma_golden_cross": False,
        "price_cross_ma25": False,
        "price_cross_ma75": False,
        "macd_golden_cross": False,
        "rsi_rebound": False,
        "pullback_buy": False,
    }
    if len(recent_prices) < _BUY_SIGNAL_MIN_LEN:
        return result

    # 古い順（末尾が最新）に並べ替え
    closes: list[Decimal | None] = [p.close_price for p in reversed(recent_prices)]
    n = len(closes)

    if need_ma:
        # compute_sma は list[Decimal] 前提。closes は全て非 None
        closes_nonnull = [c for c in closes if c is not None]
        sma25 = compute_sma(closes_nonnull, 25)
        sma75 = compute_sma(closes_nonnull, 75)
        result["ma_golden_cross"] = _crossed_up(sma25, sma75, require_below=True)
        result["price_cross_ma25"] = _crossed_up(closes, sma25, require_below=True)
        result["price_cross_ma75"] = _crossed_up(closes, sma75, require_below=True)
        # 押し目買い: 終値が25日線を直近5日で上抜け、かつその時点で 25日線 > 75日線（上昇トレンド継続）
        for i in range(max(1, n - _RECENT_WINDOW), n):
            c_prev, c_curr = closes[i - 1], closes[i]
            m25_prev, m25_curr, m75_curr = sma25[i - 1], sma25[i], sma75[i]
            if None in (c_prev, c_curr, m25_prev, m25_curr, m75_curr):
                continue
            if c_prev <= m25_prev and c_curr > m25_curr and m25_curr > m75_curr:  # type: ignore[operator]
                result["pullback_buy"] = True
                break

    if need_macd:
        closes_nonnull = [c for c in closes if c is not None]
        _, _, hist = compute_macd(closes_nonnull, 12, 26, 9)
        # ヒストグラムが負→正（MACDがシグナル線を上抜け）を直近5日で検出
        for i in range(max(1, len(hist) - _RECENT_WINDOW), len(hist)):
            prev, curr = hist[i - 1], hist[i]
            if prev is None or curr is None:
                continue
            if prev <= 0 and curr > 0:
                result["macd_golden_cross"] = True
                break

    if need_rsi:
        closes_nonnull = [c for c in closes if c is not None]
        rsi = compute_rsi(closes_nonnull, 14)
        result["rsi_rebound"] = _rebound_up(rsi, Decimal("30"))

    return result


def compute_technical_metrics(
    latest_price: Decimal | None,
    high_low: tuple[Decimal, Decimal] | None,
    recent_prices: list[PriceEntity],
    *,
    need_ma: bool = False,
    need_macd: bool = False,
    need_rsi: bool = False,
) -> TechnicalMetrics:
    """テクニカル指標を計算する。

    Args:
        latest_price: 直近の株価。
        high_low: (52w高値, 52w安値) タプル。データなしは None。
        recent_prices: 日付降順の直近株価リスト（最大25件）。MA25・出来高比率計算用。
    """
    if latest_price is None or high_low is None:
        # 52週データが無くても、価格系列があれば買い時シグナルは判定できる
        buy = _compute_buy_signals(recent_prices, need_ma=need_ma, need_macd=need_macd, need_rsi=need_rsi)
        return TechnicalMetrics(
            price_position_52w=None,
            near_52w_high=None,
            distance_from_52w_high=None,
            volume_ratio_20d=None,
            ma_25_deviation=None,
            momentum_signal=None,
            avg_turnover_20d=None,
            ma_golden_cross=buy["ma_golden_cross"],
            price_cross_ma25=buy["price_cross_ma25"],
            price_cross_ma75=buy["price_cross_ma75"],
            macd_golden_cross=buy["macd_golden_cross"],
            rsi_rebound=buy["rsi_rebound"],
            pullback_buy=buy["pullback_buy"],
        )

    high, low = high_low

    # 52週レンジ内の位置
    price_range = high - low
    if price_range > 0:
        position = ((latest_price - low) / price_range).quantize(Decimal("0.0001"))
    else:
        position = Decimal("1.0000")  # 高値=安値の場合

    # 52週高値近接フラグ
    near_high = position >= Decimal("0.95")

    # 52週高値からの乖離率
    distance = ((latest_price - high) / high).quantize(Decimal("0.0001")) if high > 0 else None

    # 出来高比率（5日平均 / 20日平均）
    volume_ratio: Decimal | None = None
    volumes = [p.volume for p in recent_prices if p.volume is not None and p.volume > 0]
    if len(volumes) >= 20:
        avg_5 = Decimal(sum(volumes[:5])) / Decimal("5")
        avg_20 = Decimal(sum(volumes[:20])) / Decimal("20")
        if avg_20 > 0:
            volume_ratio = (avg_5 / avg_20).quantize(Decimal("0.01"))

    # 25日移動平均乖離率
    ma_25_dev: Decimal | None = None
    closes = [p.close_price for p in recent_prices]
    if len(closes) >= 25:
        ma_25 = sum(closes[:25]) / Decimal("25")
        if ma_25 > 0:
            ma_25_dev = ((latest_price - ma_25) / ma_25).quantize(Decimal("0.0001"))

    # 売買代金20日平均（出来高 × 終値）
    avg_turnover: Decimal | None = None
    turnovers = [Decimal(p.volume) * p.close_price for p in recent_prices[:20] if p.volume is not None and p.volume > 0]
    if len(turnovers) >= 20:
        avg_turnover = (sum(turnovers) / Decimal("20")).quantize(Decimal("1"))

    # モメンタムシグナル
    signal = _compute_momentum_signal(position, volume_ratio, ma_25_dev)

    # 買い時シグナル（該当フィルタ利用時のみ計算。不要なら全 False）
    buy = _compute_buy_signals(recent_prices, need_ma=need_ma, need_macd=need_macd, need_rsi=need_rsi)

    return TechnicalMetrics(
        price_position_52w=position,
        near_52w_high=near_high,
        distance_from_52w_high=distance,
        volume_ratio_20d=volume_ratio,
        ma_25_deviation=ma_25_dev,
        momentum_signal=signal,
        avg_turnover_20d=avg_turnover,
        ma_golden_cross=buy["ma_golden_cross"],
        price_cross_ma25=buy["price_cross_ma25"],
        price_cross_ma75=buy["price_cross_ma75"],
        macd_golden_cross=buy["macd_golden_cross"],
        rsi_rebound=buy["rsi_rebound"],
        pullback_buy=buy["pullback_buy"],
    )


def compute_volatility_20d(recent_prices: list[PriceEntity]) -> Decimal | None:
    """過去20営業日の日次リターン標準偏差を百分率で返す。

    recent_prices は **日付降順**（先頭が最新）を前提とする。
    21件以上ないと20日分のリターンが計算できないため None を返す。
    """
    if len(recent_prices) < 21:  # noqa: PLR2004
        return None
    # 先頭21件 = 最新21日。日付降順 → 古い順に並べ直す
    closes_recent = [p.close_price for p in recent_prices[:21]]
    closes = list(reversed(closes_recent))  # 古い → 新しい

    returns: list[Decimal] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev <= 0:
            return None
        returns.append((closes[i] - prev) / prev)

    n = Decimal(len(returns))
    mean = sum(returns, Decimal(0)) / n
    variance = sum((r - mean) ** 2 for r in returns) / n
    # Decimal は sqrt 直接サポートなし → float 経由
    std_dev_float = float(variance) ** 0.5
    return (Decimal(str(std_dev_float)) * Decimal("100")).quantize(Decimal("0.01"))


@dataclass
class RangeMetrics1y:
    """1年(252営業日)レンジ指標。"""

    high: Decimal  # 期間中の終値ベース最高値
    low: Decimal  # 期間中の終値ベース最安値
    range_width: Decimal  # high - low（円）
    range_pct: Decimal  # (high - low) / low（比率）
    drift_pct: Decimal  # (期末close - 期初close) / 期初close


def compute_range_metrics_1y(recent_prices: list[PriceEntity]) -> RangeMetrics1y | None:
    """過去1年(最大252営業日)のレンジ指標を返す。

    recent_prices は **日付降順** を前提（先頭が最新）。
    100営業日に満たない銘柄は None を返す（レンジ判定の信頼性を確保）。
    """
    min_days = 100
    if len(recent_prices) < min_days:
        return None

    last_252 = recent_prices[:252]  # 直近1年分（最大252営業日）
    closes = [p.close_price for p in last_252]

    high = max(closes)
    low = min(closes)
    if low <= 0:
        return None

    range_width = high - low
    range_pct = ((high - low) / low).quantize(Decimal("0.0001"))

    # 期初 = 一番古い、期末 = 一番新しい（日付降順なので末尾が古い、先頭が新しい）
    first_close = last_252[-1].close_price
    last_close = last_252[0].close_price
    if first_close <= 0:
        return None
    drift_pct = ((last_close - first_close) / first_close).quantize(Decimal("0.0001"))

    return RangeMetrics1y(
        high=high,
        low=low,
        range_width=range_width,
        range_pct=range_pct,
        drift_pct=drift_pct,
    )
