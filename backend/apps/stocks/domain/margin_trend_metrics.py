"""信用残高トレンドメトリクスの算出ロジック。

信用買残は将来の売り圧力（需給の重し）となるため、
決算利益が伸びている一方で買残が減少している銘柄は
需給改善による株価の伸びしろが期待できる、という観点で用いる。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.entities import MarginBalanceEntity

# 信用残高は週次（週末値）で公表されるため、1ヶ月 ≒ 4.345 週として換算する
_WEEKS_PER_MONTH = Decimal("4.345")

# 「横ばい」とみなす変化率の閾値(%)。これ未満の増減はノイズとして方向を出さない
_FLAT_THRESHOLD = Decimal("1")

# 指定期間に対して最低限必要な履歴の割合（週次の欠測を許容するための係数）
_MIN_HISTORY_RATIO = 0.8


@dataclass
class MarginTrendMetrics:
    """信用残高トレンドメトリクス。"""

    long_balance_change_pct: Decimal | None  # 指定期間の信用買残の変化率 (%)
    long_balance_trend: str | None  # "increasing" / "decreasing" / "flat"
    long_balance_weeks_span: int | None  # 実際に比較に使った週数（データ不足の判断用）


def compute_margin_trend_metrics(
    recent_margins: list[MarginBalanceEntity],
    months: int,
) -> MarginTrendMetrics:
    """信用買残の変化率とトレンドを算出する。

    Args:
        recent_margins: 対象銘柄の信用残高（date 降順、先頭が最新）
        months: 遡る期間（月数）

    比較は「最新値」と「months ヶ月前に最も近い時点の値」の 2 点で行う。
    指定期間に満たないデータしか無い場合は None を返す（誤判定を避けるため、
    手前のデータで代用しない）。
    """
    empty = MarginTrendMetrics(
        long_balance_change_pct=None,
        long_balance_trend=None,
        long_balance_weeks_span=None,
    )

    if months <= 0:
        return empty

    # 買残が入っているレコードのみを対象にする
    points = [m for m in recent_margins if m.long_balance is not None]
    if len(points) < 2:  # noqa: PLR2004
        return empty

    # date 降順を保証（呼び出し側の並びに依存しない）
    points = sorted(points, key=lambda m: m.date, reverse=True)

    latest = points[0]
    target_weeks = int((Decimal(months) * _WEEKS_PER_MONTH).to_integral_value())

    # 十分に遡れているか（指定期間の 8 割に満たない履歴しか無い場合は判定不能）
    oldest_weeks_apart = (latest.date - points[-1].date).days / 7
    if oldest_weeks_apart < target_weeks * _MIN_HISTORY_RATIO:
        return empty

    # 指定期間に「最も近い」点を基準にする（週次の欠測があっても前後どちらかで拾える）
    baseline = min(
        points[1:],
        key=lambda m: abs((latest.date - m.date).days / 7 - target_weeks),
    )

    latest_value = latest.long_balance
    baseline_value = baseline.long_balance
    if latest_value is None or baseline_value is None or baseline_value <= 0:
        return empty

    change_pct = (
        (Decimal(latest_value) - Decimal(baseline_value)) / Decimal(baseline_value) * Decimal("100")
    ).quantize(Decimal("0.01"))

    if change_pct > _FLAT_THRESHOLD:
        trend = "increasing"
    elif change_pct < -_FLAT_THRESHOLD:
        trend = "decreasing"
    else:
        trend = "flat"

    weeks_span = int((latest.date - baseline.date).days / 7)

    return MarginTrendMetrics(
        long_balance_change_pct=change_pct,
        long_balance_trend=trend,
        long_balance_weeks_span=weeks_span,
    )
