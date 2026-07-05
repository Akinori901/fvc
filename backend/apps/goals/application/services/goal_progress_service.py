"""目標進捗計算サービス。

達成率・GAP・予測値・チャート系列を一括算出。
信用口座補正は portfolios の `_effective_account_value` を再利用。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from apps.portfolios.presentation.views import _effective_account_value

if TYPE_CHECKING:
    from apps.goals.domain.entities import FinancialGoalEntity
    from apps.portfolios.domain.entities import (
        AccountSnapshotEntity,
        FamilyMemberEntity,
        PortfolioAccountEntity,
    )


@dataclass
class GoalProgressResult:
    current_value_jpy: Decimal
    achievement_rate_pct: Decimal  # 達成率 = current/target × 100
    ideal_value_now_jpy: Decimal  # 進捗線上の現時点値
    gap_jpy: Decimal  # current - ideal
    avg_monthly_increase_jpy: Decimal | None
    projected_value_at_target_jpy: Decimal | None
    projection_status: str  # "ahead" | "on_track" | "behind" | "unknown"
    chart: list[
        dict[str, object]
    ]  # [{"date": "YYYY-MM-DD", "actual": 数値|None, "ideal": 数値|None, "projected": 数値|None}]


class GoalProgressService:
    """目標進捗計算（純粋ロジック、I/Oは外で実行）"""

    def compute(
        self,
        goal: FinancialGoalEntity,
        members: list[FamilyMemberEntity],
        accounts: list[PortfolioAccountEntity],
        latest_snapshots: list[AccountSnapshotEntity],
        all_snapshots: list[AccountSnapshotEntity],
        today: datetime.date | None = None,
    ) -> GoalProgressResult:
        today = today or datetime.date.today()

        # 1. ターゲットメンバーIDを確定
        target_member_ids = self._resolve_target_member_ids(goal, members)
        # 2. ターゲット口座IDセット
        account_is_margin: dict[int, bool] = {}
        target_account_ids: set[int] = set()
        for acc in accounts:
            if acc.id is None:
                continue
            if acc.family_member_id in target_member_ids:
                target_account_ids.add(acc.id)
                account_is_margin[acc.id] = acc.trading_type == "margin"

        # 3. 現在価値（信用補正適用）
        current_value = Decimal(0)
        for s in latest_snapshots:
            if s.account_id not in target_account_ids:
                continue
            current_value += _effective_account_value(
                s.total_value_jpy, s.total_cost_jpy, account_is_margin.get(s.account_id, False)
            )

        # 4. 月次系列
        monthly_actual: dict[str, Decimal] = self._build_monthly_actual(
            target_account_ids, account_is_margin, all_snapshots
        )

        # 5. 目標期間の月リスト
        target_date = datetime.date.fromisoformat(goal.target_date)
        start_date = (goal.created_at.date() if goal.created_at else today).replace(day=1)
        # 過去実績の最古月もカバーするため、actual の最古月と start_date の小さい方を起点
        if monthly_actual:
            earliest_actual = min(monthly_actual.keys())
            ed = datetime.date.fromisoformat(earliest_actual)
            if ed < start_date:
                start_date = ed
        chart_months = self._iterate_months(start_date, target_date)

        # 6. メトリクス算出
        target_value = Decimal(goal.target_value_jpy)
        months_total = max(self._month_diff(start_date, target_date), 1)
        months_elapsed = max(min(self._month_diff(start_date, today), months_total), 0)
        ideal_value_now = target_value * Decimal(months_elapsed) / Decimal(months_total)
        gap = current_value - ideal_value_now
        achievement_rate = (current_value / target_value * Decimal(100)) if target_value > 0 else Decimal(0)

        # 7. 過去12ヶ月の平均増加額
        avg_monthly_increase = self._compute_avg_monthly_increase(monthly_actual, today)

        # 8. 予測値
        months_remaining = max(self._month_diff(today, target_date), 0)
        if avg_monthly_increase is None or months_remaining == 0:
            projected_value = None
        else:
            projected_value = current_value + avg_monthly_increase * Decimal(months_remaining)

        # 9. 達成見込みステータス
        projection_status = self._compute_projection_status(projected_value, target_value)

        # 10. チャート系列
        chart = self._build_chart(
            chart_months,
            monthly_actual,
            target_value,
            start_date,
            target_date,
            today,
            current_value,
            avg_monthly_increase,
        )

        return GoalProgressResult(
            current_value_jpy=current_value.quantize(Decimal("1")),
            achievement_rate_pct=achievement_rate.quantize(Decimal("0.01")),
            ideal_value_now_jpy=ideal_value_now.quantize(Decimal("1")),
            gap_jpy=gap.quantize(Decimal("1")),
            avg_monthly_increase_jpy=(
                avg_monthly_increase.quantize(Decimal("1")) if avg_monthly_increase is not None else None
            ),
            projected_value_at_target_jpy=(
                projected_value.quantize(Decimal("1")) if projected_value is not None else None
            ),
            projection_status=projection_status,
            chart=chart,
        )

    # ───── ヘルパー ─────

    def _resolve_target_member_ids(self, goal: FinancialGoalEntity, members: list[FamilyMemberEntity]) -> set[int]:
        if goal.scope_type == "family":
            return {m.id for m in members if m.include_in_family_total and m.id is not None}
        # members
        return set(goal.member_ids)

    def _build_monthly_actual(
        self,
        target_account_ids: set[int],
        account_is_margin: dict[int, bool],
        all_snapshots: list[AccountSnapshotEntity],
    ) -> dict[str, Decimal]:
        """月初日(YYYY-MM-01)→補正後合計のマップ。

        各口座について、月内の最後の snapshot を採用してその月の値とする。
        """
        # 口座×月 → 最新スナップショット
        per_account: dict[tuple[int, str], AccountSnapshotEntity] = {}
        for s in all_snapshots:
            if s.account_id not in target_account_ids:
                continue
            month_key = s.snapshot_date[:7] + "-01"
            existing = per_account.get((s.account_id, month_key))
            if existing is None or s.snapshot_date > existing.snapshot_date:
                per_account[(s.account_id, month_key)] = s

        # 月単位で集計
        monthly: dict[str, Decimal] = {}
        for (acc_id, month_key), s in per_account.items():
            eff = _effective_account_value(s.total_value_jpy, s.total_cost_jpy, account_is_margin.get(acc_id, False))
            monthly[month_key] = monthly.get(month_key, Decimal(0)) + eff
        return monthly

    def _iterate_months(self, start: datetime.date, end: datetime.date) -> list[str]:
        """start月初〜end月初まで（両端含む）の月リスト。"""
        cur = start.replace(day=1)
        end_first = end.replace(day=1)
        result: list[str] = []
        while cur <= end_first:
            result.append(cur.isoformat())
            # 次の月
            cur = (
                datetime.date(cur.year + 1, 1, 1)
                if cur.month == 12  # noqa: PLR2004
                else datetime.date(cur.year, cur.month + 1, 1)
            )
        return result

    def _month_diff(self, start: datetime.date, end: datetime.date) -> int:
        return (end.year - start.year) * 12 + (end.month - start.month)

    def _compute_avg_monthly_increase(self, monthly_actual: dict[str, Decimal], today: datetime.date) -> Decimal | None:
        if not monthly_actual:
            return None
        sorted_months = sorted(monthly_actual.keys())
        latest_key = sorted_months[-1]
        latest_val = monthly_actual[latest_key]

        # 12ヶ月前のキー候補
        latest_date = datetime.date.fromisoformat(latest_key)
        target_y = latest_date.year - 1 if latest_date.month >= 1 else latest_date.year - 1
        target_key = f"{target_y:04d}-{latest_date.month:02d}-01"

        if target_key in monthly_actual:
            past_val = monthly_actual[target_key]
            return (latest_val - past_val) / Decimal(12)

        # 12ヶ月分なければ取得可能な期間で平均
        earliest_key = sorted_months[0]
        earliest_val = monthly_actual[earliest_key]
        months_span = self._month_diff(datetime.date.fromisoformat(earliest_key), latest_date)
        if months_span <= 0:
            return None
        return (latest_val - earliest_val) / Decimal(months_span)

    def _compute_projection_status(self, projected: Decimal | None, target: Decimal) -> str:
        if projected is None or target <= 0:
            return "unknown"
        ratio = projected / target
        if ratio >= Decimal("1.05"):
            return "ahead"
        if ratio >= Decimal("0.95"):
            return "on_track"
        return "behind"

    def _build_chart(
        self,
        months: list[str],
        actual: dict[str, Decimal],
        target_value: Decimal,
        start: datetime.date,
        end: datetime.date,
        today: datetime.date,
        current_value: Decimal,
        avg_monthly_increase: Decimal | None,
    ) -> list[dict[str, object]]:
        months_total = max(self._month_diff(start, end), 1)
        today_first = today.replace(day=1)
        chart: list[dict[str, object]] = []
        for m in months:
            d = datetime.date.fromisoformat(m)
            elapsed = self._month_diff(start, d)
            ideal = target_value * Decimal(min(max(elapsed, 0), months_total)) / Decimal(months_total)
            point: dict[str, object] = {
                "date": m,
                "actual": int(actual[m]) if m in actual else None,
                "ideal": int(ideal),
                "projected": None,
            }
            # 予測線: 今月以降のみ
            if d >= today_first and avg_monthly_increase is not None:
                months_from_today = self._month_diff(today_first, d)
                projected = current_value + avg_monthly_increase * Decimal(months_from_today)
                point["projected"] = int(projected)
            chart.append(point)
        return chart
