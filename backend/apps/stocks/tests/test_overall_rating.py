"""総合評価スコア（compute_overall_score）の golden vector テスト。

fixtures/overall_rating_golden.json は FE(overallRating.test.ts) と共有し、
TS/Python の数値一致を担保する。ケースを変えたら両テストを再実行すること。
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from apps.stocks.domain.overall_rating import OverallRatingInputs, compute_overall_score

_GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "overall_rating_golden.json").read_text(encoding="utf-8"))


def _d(v: str | None) -> Decimal | None:
    return Decimal(v) if v is not None else None


@pytest.mark.parametrize("case", _GOLDEN["cases"], ids=[c["name"] for c in _GOLDEN["cases"]])
def test_overall_score_matches_golden(case: dict[str, Any]) -> None:
    i = case["inputs"]
    inputs = OverallRatingInputs(
        evaluation_zone=i["evaluation_zone"],
        growth_rate_label=i["growth_rate_label"],
        roe_trend=i["roe_trend"],
        eps_cagr_3y=_d(i["eps_cagr_3y"]),
        eps_growth_yoy=_d(i["eps_growth_yoy"]),
        sl_ratio=_d(i["sl_ratio"]),
        momentum_signal=i["momentum_signal"],
        dividend_yield=_d(i["dividend_yield"]),
        payout_ratio=_d(i["payout_ratio"]),
        consecutive_dividend_years=i["consecutive_dividend_years"],
        progressive_dividend_years=i["progressive_dividend_years"],
        fcf_yield=_d(i["fcf_yield"]),
        fcf_margin=_d(i["fcf_margin"]),
        fcf=i["fcf"],
        prev_fcf=i["prev_fcf"],
    )
    assert compute_overall_score(inputs) == case["expected_score"]
