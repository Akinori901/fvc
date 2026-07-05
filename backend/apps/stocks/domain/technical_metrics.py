"""52週高値効果テクニカル指標の計算ロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import PriceEntity


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


def compute_technical_metrics(
    latest_price: Decimal | None,
    high_low: tuple[Decimal, Decimal] | None,
    recent_prices: list[PriceEntity],
) -> TechnicalMetrics:
    """テクニカル指標を計算する。

    Args:
        latest_price: 直近の株価。
        high_low: (52w高値, 52w安値) タプル。データなしは None。
        recent_prices: 日付降順の直近株価リスト（最大25件）。MA25・出来高比率計算用。
    """
    if latest_price is None or high_low is None:
        return TechnicalMetrics(None, None, None, None, None, None, None)

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

    return TechnicalMetrics(
        price_position_52w=position,
        near_52w_high=near_high,
        distance_from_52w_high=distance,
        volume_ratio_20d=volume_ratio,
        ma_25_deviation=ma_25_dev,
        momentum_signal=signal,
        avg_turnover_20d=avg_turnover,
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
