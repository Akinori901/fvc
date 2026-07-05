"""FCF（フリーキャッシュフロー）評価メトリクスの算出ロジック。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class FcfMetrics:
    """FCF評価メトリクス。"""

    fcf: int | None  # FCF（百万円）
    fcf_yield: Decimal | None  # FCF利回り (%)
    fcf_margin: Decimal | None  # FCFマージン (%)
    fcf_score: int | None  # FCFスコア (-2 ~ +2)


def compute_fcf_metrics(
    latest_fcf: int | None,
    prev_fcf: int | None,
    market_cap: Decimal | None,
    revenue: int | None,
) -> FcfMetrics:
    """FCF評価メトリクスを算出する。

    Args:
        latest_fcf: 直近期のFCF（百万円）
        prev_fcf: 前期のFCF（百万円）
        market_cap: 時価総額（円）= 株価 × 発行済株式数
        revenue: 売上高（百万円）
    """
    if latest_fcf is None:
        return FcfMetrics(fcf=None, fcf_yield=None, fcf_margin=None, fcf_score=None)

    # FCF利回り = FCF(百万円) / 時価総額(百万円) × 100
    fcf_yield: Decimal | None = None
    if market_cap is not None and market_cap > 0:
        market_cap_m = market_cap / Decimal("1000000")  # 円→百万円
        if market_cap_m > 0:
            fcf_yield = (Decimal(latest_fcf) / market_cap_m * Decimal("100")).quantize(Decimal("0.01"))

    # FCFマージン = FCF / 売上高 × 100
    fcf_margin: Decimal | None = None
    if revenue is not None and revenue > 0:
        fcf_margin = (Decimal(latest_fcf) / Decimal(revenue) * Decimal("100")).quantize(Decimal("0.01"))

    score = _compute_fcf_score(latest_fcf, prev_fcf, fcf_yield, fcf_margin)

    return FcfMetrics(
        fcf=latest_fcf,
        fcf_yield=fcf_yield,
        fcf_margin=fcf_margin,
        fcf_score=score,
    )


def _compute_fcf_score(
    latest_fcf: int,
    prev_fcf: int | None,
    fcf_yield: Decimal | None,
    fcf_margin: Decimal | None,
) -> int:
    """FCFスコアを算出。-2 〜 +2。"""
    # FCFマイナス判定
    if latest_fcf < 0:
        if prev_fcf is not None and prev_fcf < 0:
            return -2  # 2期連続マイナス
        return -1  # 1期のみマイナス

    # FCF利回り ≥ 8% かつ FCFマージン ≥ 10%
    high_yield = fcf_yield is not None and fcf_yield >= Decimal("8")
    high_margin = fcf_margin is not None and fcf_margin >= Decimal("10")
    if high_yield and high_margin:
        return 2

    # FCF利回り ≥ 5%
    if fcf_yield is not None and fcf_yield >= Decimal("5"):
        return 1

    # FCF ≥ 0
    return 0
