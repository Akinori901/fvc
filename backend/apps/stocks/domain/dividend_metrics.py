"""配当評価メトリクスの算出ロジック。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import DividendEntity


@dataclass
class DividendMetrics:
    """配当評価メトリクス。データ不足の場合は各フィールドが None になる。"""

    dividend_yield: Decimal | None  # 配当利回り (%)
    payout_ratio: Decimal | None  # 配当性向 (%)
    consecutive_dividend_years: int | None  # 連続配当年数
    progressive_dividend_years: int | None  # 累進配当年数
    dividend_score: int | None  # 配当スコア (-2 ~ +2)


def _aggregate_annual_dividends(dividends: list[DividendEntity]) -> dict[int, Decimal]:
    """配当履歴を暦年単位の年間合計に集約。"""
    annual: dict[int, Decimal] = defaultdict(Decimal)
    for d in dividends:
        annual[d.ex_dividend_date.year] += d.dividends_per_share
    return dict(annual)


def _compute_consecutive_years(annual_dividends: dict[int, Decimal]) -> int:
    """現在から遡って何年連続で配当があるか。今年は未確定のため前年起算。"""
    current_year = date.today().year
    count = 0
    for year in range(current_year - 1, current_year - 31, -1):
        if annual_dividends.get(year, Decimal("0")) > 0:
            count += 1
        else:
            break
    return count


def _compute_progressive_years(annual_dividends: dict[int, Decimal]) -> int:
    """現在から遡って何年連続で減配していないか（維持 or 増配）。"""
    current_year = date.today().year
    years = sorted(
        [y for y in annual_dividends if y < current_year],
        reverse=True,
    )

    if len(years) < 2:  # noqa: PLR2004
        return 0

    count = 0
    for i in range(len(years) - 1):
        this_year = years[i]
        prev_year = years[i + 1]
        # 連続する年でない場合は打ち切り
        if this_year - prev_year != 1:
            break
        if annual_dividends[this_year] >= annual_dividends[prev_year]:
            count += 1
        else:
            break
    return count


def _compute_dividend_score(
    dividend_yield: Decimal | None,
    payout_ratio: Decimal | None,
    consecutive_years: int,
    progressive_years: int,
) -> int:
    """配当スコアを算出。-2 〜 +2。"""
    # 無配
    if dividend_yield is None or dividend_yield == Decimal("0"):
        return -1

    high_yield = dividend_yield >= Decimal("3.5")
    healthy_payout = payout_ratio is None or payout_ratio <= Decimal("60")
    risky_payout = payout_ratio is not None and payout_ratio > Decimal("70")

    # 高配当 + 高性向（危険）
    if high_yield and risky_payout:
        if progressive_years == 0:
            return -2
        return -1

    # 高配当 + 健全性向
    if high_yield and healthy_payout:
        if progressive_years >= 3:  # noqa: PLR2004
            return 2
        return 1

    # 配当あり + 連続配当 ≥ 5年
    if consecutive_years >= 5:  # noqa: PLR2004
        return 1

    # 普通の配当
    return 0


def compute_dividend_metrics(
    dividends: list[DividendEntity],
    annual_total: Decimal | None,
    latest_price: Decimal | None,
    eps: Decimal | None,
) -> DividendMetrics:
    """配当評価メトリクスを算出する。

    Args:
        dividends: 全配当履歴（連続配当・累進配当の算出用）
        annual_total: 直近12ヶ月の配当合計
        latest_price: 最新株価
        eps: 直近EPS
    """
    # 配当データなし
    if annual_total is None or annual_total <= 0:
        return DividendMetrics(
            dividend_yield=None,
            payout_ratio=None,
            consecutive_dividend_years=0 if dividends else None,
            progressive_dividend_years=0 if dividends else None,
            dividend_score=-1 if dividends else None,
        )

    # 配当利回り
    dy: Decimal | None = None
    if latest_price and latest_price > 0:
        dy = (annual_total / latest_price * Decimal("100")).quantize(Decimal("0.01"))

    # 配当性向
    pr: Decimal | None = None
    if eps and eps > 0:
        pr = (annual_total / eps * Decimal("100")).quantize(Decimal("0.01"))

    # 連続配当・累進配当
    annual = _aggregate_annual_dividends(dividends)
    consecutive = _compute_consecutive_years(annual)
    progressive = _compute_progressive_years(annual)

    score = _compute_dividend_score(dy, pr, consecutive, progressive)

    return DividendMetrics(
        dividend_yield=dy,
        payout_ratio=pr,
        consecutive_dividend_years=consecutive,
        progressive_dividend_years=progressive,
        dividend_score=score,
    )
