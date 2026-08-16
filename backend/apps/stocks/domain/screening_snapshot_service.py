"""スナップショットの growth_rate 依存部分をリクエスト時に再計算するサービス。

t_screening_snapshots には growth_rate 非依存の生値・指標だけを保存している。
一覧API はリクエストの growth_rate を受けて、適正株価・乖離率・評価ゾーン・
市場折込成長率・総合評価スコアだけをここで軽量に再計算する（全銘柄でも四則演算）。

計算ロジックは screening_usecase.execute の適正株価ブロックと一致させている。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.stocks.application.usecases.screening_usecase import _get_evaluation_zone
from apps.stocks.domain.overall_rating import OverallRatingInputs, compute_overall_score
from apps.valuations.domain.entities import MARKET_COST_OF_CAPITAL, FairValueCalculation, growth_rate_label

if TYPE_CHECKING:
    from apps.stocks.models import ScreeningSnapshot


def _d(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


def apply_growth_rate(snap: ScreeningSnapshot, growth_rate: Decimal) -> dict[str, Any]:
    """スナップショット1行 + growth_rate から評価系の値を再計算して返す。

    返す値（すべて str 化 or None。フロントの ScreeningResult と同じ形）:
      current_pbr, fair_pbr, fair_value, discount_rate, evaluation_zone,
      implied_growth_rate, growth_rate_label, overall_score
    """
    m = snap.metrics or {}
    market_type = snap.market_type or "JP"
    cost_of_capital = MARKET_COST_OF_CAPITAL.get(market_type, MARKET_COST_OF_CAPITAL["JP"])

    roe = snap.roe
    bps = _d(m.get("bps"))
    latest_price = _d(m.get("latest_price"))
    can_calculate = growth_rate < cost_of_capital

    result: dict[str, Any] = {
        "current_pbr": m.get("current_pbr"),
        "fair_pbr": None,
        "fair_value": None,
        "discount_rate": None,
        "evaluation_zone": None,
        "implied_growth_rate": None,
        "growth_rate_label": None,
        "overall_score": None,
    }

    calculable = (
        can_calculate and latest_price is not None and bps is not None and bps > 0 and roe is not None and roe > 0
    )
    if not calculable:
        # 評価不能でも総合評価スコアは非評価カテゴリで算出（evaluation_zone/label は None）
        result["overall_score"] = _score(snap, m, evaluation_zone=None, growth_rate_label_val=None)
        return result

    assert bps is not None
    assert latest_price is not None
    assert roe is not None
    calc = FairValueCalculation(
        growth_rate=growth_rate,
        bps=bps,
        current_price=latest_price,
        roe=roe,
        cost_of_capital=cost_of_capital,
    )

    current_pbr = calc.current_pbr
    result["current_pbr"] = str(current_pbr)
    result["fair_pbr"] = str(calc.fair_pbr)
    result["fair_value"] = str(calc.fair_value)

    if calc.fair_value > 0:
        discount = calc.discount_rate
        evaluation_zone = _get_evaluation_zone(discount)
        result["discount_rate"] = str(discount)
    else:
        evaluation_zone = "very_expensive"
    result["evaluation_zone"] = evaluation_zone

    # 市場折込成長率と成長率評価ラベル（screening_usecase と同じ分岐）
    gr_label: str | None = None
    try:
        implied = calc.implied_growth_rate
        result["implied_growth_rate"] = str(implied)
        if current_pbr < Decimal("1") and implied >= cost_of_capital:
            gr_label = "ROE持続性に疑念"
        elif implied < cost_of_capital:
            gr_label = growth_rate_label(implied)
    except Exception:  # noqa: BLE001 - PBR≈1 の特異点等
        pass
    result["growth_rate_label"] = gr_label

    result["overall_score"] = _score(snap, m, evaluation_zone=evaluation_zone, growth_rate_label_val=gr_label)
    return result


def _score(
    snap: ScreeningSnapshot,
    m: dict[str, Any],
    *,
    evaluation_zone: str | None,
    growth_rate_label_val: str | None,
) -> int:
    return compute_overall_score(
        OverallRatingInputs(
            evaluation_zone=evaluation_zone,
            growth_rate_label=growth_rate_label_val,
            roe_trend=snap.roe_trend,
            eps_cagr_3y=_d(m.get("eps_cagr_3y")),
            eps_growth_yoy=_d(m.get("eps_growth_yoy")),
            sl_ratio=snap.sl_ratio,
            momentum_signal=snap.momentum_signal,
            dividend_yield=snap.dividend_yield,
            payout_ratio=_d(m.get("payout_ratio")),
            consecutive_dividend_years=m.get("consecutive_dividend_years"),
            progressive_dividend_years=m.get("progressive_dividend_years"),
            fcf_yield=snap.fcf_yield,
            fcf_margin=_d(m.get("fcf_margin")),
            fcf=m.get("fcf"),
            prev_fcf=m.get("prev_fcf"),
        )
    )
