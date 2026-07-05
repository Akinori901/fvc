"""FX分析 DTO。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..domain.entities import FxAnalysisResult


def fx_analysis_to_dict(result: FxAnalysisResult) -> dict[str, Any]:
    """FxAnalysisResult をAPIレスポンス用 dict に変換。"""
    regression = None
    if result.regression:
        r = result.regression
        regression = {
            "beta_0": str(r.beta_0),
            "beta_1": str(r.beta_1),
            "fair_value": str(r.fair_value),
            "residual_std": str(r.residual_std),
            "r_squared": str(r.r_squared),
            "current_deviation": str(r.current_deviation),
            "zone": r.zone,
        }

    technicals = {
        "rsi_14": str(result.technicals.rsi_14) if result.technicals.rsi_14 is not None else None,
        "bb_upper": str(result.technicals.bb_upper) if result.technicals.bb_upper is not None else None,
        "bb_middle": str(result.technicals.bb_middle) if result.technicals.bb_middle is not None else None,
        "bb_lower": str(result.technicals.bb_lower) if result.technicals.bb_lower is not None else None,
        "ma_200": str(result.technicals.ma_200) if result.technicals.ma_200 is not None else None,
        "ma_200_deviation": (
            str(result.technicals.ma_200_deviation) if result.technicals.ma_200_deviation is not None else None
        ),
    }

    return {
        "current_rate": str(result.current_rate),
        "current_rate_date": result.current_rate_date.isoformat(),
        "us_10y": str(result.us_10y) if result.us_10y is not None else None,
        "jp_10y": str(result.jp_10y) if result.jp_10y is not None else None,
        "interest_rate_diff": str(result.interest_rate_diff) if result.interest_rate_diff is not None else None,
        "regression": regression,
        "technicals": technicals,
        "ppp_rate": str(result.ppp_rate) if result.ppp_rate is not None else None,
        "ppp_deviation": str(result.ppp_deviation) if result.ppp_deviation is not None else None,
        "buy_zone_lower": str(result.buy_zone_lower) if result.buy_zone_lower is not None else None,
        "sell_zone_upper": str(result.sell_zone_upper) if result.sell_zone_upper is not None else None,
        "strong_buy_lower": str(result.strong_buy_lower) if result.strong_buy_lower is not None else None,
        "strong_sell_upper": str(result.strong_sell_upper) if result.strong_sell_upper is not None else None,
        "chart_data": result.chart_data,
    }
