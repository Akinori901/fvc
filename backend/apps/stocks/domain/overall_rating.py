"""総合評価スコアの算出（フロント frontend/src/utils/overallRating.ts の Python 移植）。

8カテゴリ（評価ゾーン / 成長率評価 / ROEトレンド / EPS成長 / 信売比率 / モメンタム /
配当 / FCF）の impact を合算してスコアを返す。ラベル・色は表示専用のためフロントに残し、
ここでは数値スコアのみを算出する（一覧のソート・フィルタに使う）。

TS 版との数値一致は golden vector テスト（test_overall_rating.py と
frontend の overallRating.test.ts で同一入力→同一 score）で担保する。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class OverallRatingInputs:
    """総合評価スコアの入力。値が無い項目は None（＝データなし扱いで impact 0）。

    比率系（eps_cagr_3y / eps_growth_yoy）は比率スケール（0.2 = 20%）。
    %スケール系（dividend_yield / payout_ratio / fcf_yield / fcf_margin）は
    フロントと同じく既に % 値（3.5 = 3.5%）で渡す。
    """

    evaluation_zone: str | None
    growth_rate_label: str | None
    roe_trend: str | None
    eps_cagr_3y: Decimal | None
    eps_growth_yoy: Decimal | None
    sl_ratio: Decimal | None
    momentum_signal: str | None
    dividend_yield: Decimal | None
    payout_ratio: Decimal | None
    consecutive_dividend_years: int | None
    progressive_dividend_years: int | None
    fcf_yield: Decimal | None
    fcf_margin: Decimal | None
    fcf: int | None
    prev_fcf: int | None


def _valuation_impact(zone: str | None) -> int:
    return {
        "very_cheap": 3,
        "cheap": 1,
        "fair": 0,
        "expensive": -2,
        "very_expensive": -4,
    }.get(zone or "", 0)


def _growth_impact(label: str | None) -> int:
    if label == "かなり強気":
        return 2
    if label in ("非常に優秀", "優秀"):
        return 1
    if label in ("普通", "低成長"):
        return 0
    if label == "マイナス成長":
        return -1
    if label == "ROE持続性に疑念":
        return -2
    return 0


def _roe_trend_impact(trend: str | None) -> int:
    return {"improving": 1, "declining": -1, "stable": 0}.get(trend or "", 0)


def _eps_growth_impact(cagr3y: Decimal | None, yoy: Decimal | None) -> int:
    eps_growth = cagr3y if cagr3y is not None else yoy
    if eps_growth is None:
        return 0
    if eps_growth >= Decimal("0.2"):
        return 1
    if eps_growth <= Decimal("-0.2"):
        return -1
    return 0


def _margin_impact(sl_ratio: Decimal | None) -> int:
    if sl_ratio is None:
        return 0
    if sl_ratio < Decimal("0.05"):
        return -4
    if sl_ratio < Decimal("0.30"):
        return -1
    # 0.05〜2.00 は均衡(0)、2.00超も 0（TS版と一致）
    return 0


def _momentum_impact(signal: str | None) -> int:
    return {
        "strong_buy": 2,
        "buy": 1,
        "neutral": 0,
        "caution": -1,
        "sell": -1,
    }.get(signal or "", 0)


def _dividend_impact(
    dy: Decimal | None,
    pr: Decimal | None,
    consec: int | None,
    prog: int | None,
) -> int:
    if dy is None or dy == 0:
        if dy == 0:
            return -1  # 無配
        return 0  # データなし
    high_yield = dy >= Decimal("3.5")
    risky_payout = pr is not None and pr > Decimal("70")
    healthy_payout = pr is None or pr <= Decimal("60")

    if high_yield and risky_payout:
        if prog is None or prog == 0:
            return -2
        return -1
    if high_yield and healthy_payout:
        if prog is not None and prog >= 3:
            return 2
        return 1
    if consec is not None and consec >= 5:
        return 1
    return 0


def _fcf_impact(
    fcf: int | None,
    fcf_yield: Decimal | None,
    fcf_margin: Decimal | None,
    prev_fcf: int | None,
) -> int:
    if fcf is None:
        return 0
    if fcf < 0:
        if prev_fcf is not None and prev_fcf < 0:
            return -2
        return -1
    if fcf_yield is not None and fcf_yield >= Decimal("8") and fcf_margin is not None and fcf_margin >= Decimal("10"):
        return 2
    if fcf_yield is not None and fcf_yield >= Decimal("5"):
        return 1
    return 0


def compute_overall_score(inputs: OverallRatingInputs) -> int:
    """8カテゴリの impact を合算した総合評価スコアを返す。"""
    return (
        _valuation_impact(inputs.evaluation_zone)
        + _growth_impact(inputs.growth_rate_label)
        + _roe_trend_impact(inputs.roe_trend)
        + _eps_growth_impact(inputs.eps_cagr_3y, inputs.eps_growth_yoy)
        + _margin_impact(inputs.sl_ratio)
        + _momentum_impact(inputs.momentum_signal)
        + _dividend_impact(
            inputs.dividend_yield,
            inputs.payout_ratio,
            inputs.consecutive_dividend_years,
            inputs.progressive_dividend_years,
        )
        + _fcf_impact(inputs.fcf, inputs.fcf_yield, inputs.fcf_margin, inputs.prev_fcf)
    )
