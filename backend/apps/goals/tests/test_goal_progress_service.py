"""GoalProgressService 単体テスト（DBアクセスなし）。"""

import datetime
from decimal import Decimal
from typing import cast

from apps.goals.application.services.goal_progress_service import GoalProgressService
from apps.goals.domain.entities import FinancialGoalEntity
from apps.portfolios.domain.entities import (
    AccountSnapshotEntity,
    FamilyMemberEntity,
    PortfolioAccountEntity,
)


def _make_member(member_id: int, include: bool = True) -> FamilyMemberEntity:
    return FamilyMemberEntity(
        id=member_id,
        user_id=1,
        name=f"M{member_id}",
        role="self",
        include_in_family_total=include,
    )


def _make_account(acc_id: int, member_id: int, trading_type: str = "spot") -> PortfolioAccountEntity:
    return PortfolioAccountEntity(
        id=acc_id,
        family_member_id=member_id,
        institution="test",
        institution_type="securities_jp",
        asset_class="jp_stock",
        trading_type=trading_type,
    )


def _make_snapshot(acc_id: int, date: str, value: int, cost: int | None = None) -> AccountSnapshotEntity:
    return AccountSnapshotEntity(
        id=None,
        account_id=acc_id,
        snapshot_date=date,
        total_value_jpy=Decimal(value),
        total_cost_jpy=Decimal(cost) if cost is not None else None,
    )


class TestGoalProgressService:
    def test_family_scope_basic_progress(self) -> None:
        """家族合計スコープの基本進捗計算"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="5000万",
            target_value_jpy=Decimal("50000000"),
            target_date="2030-01-01",
            scope_type="family",
            created_at=datetime.datetime(2024, 1, 1),
        )
        members = [_make_member(1)]
        accounts = [_make_account(10, 1)]
        latest = [_make_snapshot(10, "2026-01-01", 25000000)]
        all_snaps = [
            _make_snapshot(10, "2025-01-01", 20000000),
            _make_snapshot(10, "2026-01-01", 25000000),
        ]
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, all_snaps, today=datetime.date(2026, 1, 15))
        assert result.current_value_jpy == Decimal("25000000")
        # 達成率 25M / 50M = 50%
        assert result.achievement_rate_pct == Decimal("50.00")

    def test_margin_account_uses_pnl_only(self) -> None:
        """信用口座は (val - cost) 損益のみ計上される"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="x",
            target_value_jpy=Decimal("10000000"),
            target_date="2030-01-01",
            scope_type="family",
            created_at=datetime.datetime(2024, 1, 1),
        )
        members = [_make_member(1)]
        accounts = [_make_account(10, 1, trading_type="margin")]
        # 時価1000万、原価800万 → 損益200万
        latest = [_make_snapshot(10, "2026-01-01", 10000000, cost=8000000)]
        all_snaps = list(latest)
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, all_snaps, today=datetime.date(2026, 1, 15))
        assert result.current_value_jpy == Decimal("2000000")

    def test_members_scope_filters_by_member_ids(self) -> None:
        """members スコープは指定メンバーのみ集計"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="x",
            target_value_jpy=Decimal("10000000"),
            target_date="2030-01-01",
            scope_type="members",
            member_ids=[1],  # member 2 は除外
            created_at=datetime.datetime(2024, 1, 1),
        )
        members = [_make_member(1), _make_member(2)]
        accounts = [_make_account(10, 1), _make_account(20, 2)]
        latest = [
            _make_snapshot(10, "2026-01-01", 5000000),
            _make_snapshot(20, "2026-01-01", 99999999),  # 除外される
        ]
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, list(latest), today=datetime.date(2026, 1, 15))
        assert result.current_value_jpy == Decimal("5000000")

    def test_avg_monthly_increase_from_12months(self) -> None:
        """過去12ヶ月の平均増加額"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="x",
            target_value_jpy=Decimal("100000000"),
            target_date="2030-01-01",
            scope_type="family",
            created_at=datetime.datetime(2024, 1, 1),
        )
        members = [_make_member(1)]
        accounts = [_make_account(10, 1)]
        latest = [_make_snapshot(10, "2026-01-01", 14000000)]
        # 12ヶ月前 (2025-01) 8M → 2026-01 14M → 6M 上昇 / 12 = 0.5M/月
        all_snaps = [
            _make_snapshot(10, "2025-01-15", 8000000),
            _make_snapshot(10, "2026-01-01", 14000000),
        ]
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, all_snaps, today=datetime.date(2026, 1, 15))
        assert result.avg_monthly_increase_jpy == Decimal("500000")

    def test_chart_includes_actual_ideal_projected(self) -> None:
        """チャート系列に actual / ideal / projected が含まれる"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="x",
            target_value_jpy=Decimal("12000000"),
            target_date="2027-01-01",
            scope_type="family",
            created_at=datetime.datetime(2026, 1, 1),
        )
        members = [_make_member(1)]
        accounts = [_make_account(10, 1)]
        latest = [_make_snapshot(10, "2026-06-01", 6000000)]
        all_snaps = [
            _make_snapshot(10, "2026-01-15", 5000000),
            _make_snapshot(10, "2026-06-01", 6000000),
        ]
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, all_snaps, today=datetime.date(2026, 6, 15))
        # 過去月には actual が入る
        actual_dates = {p["date"] for p in result.chart if p["actual"] is not None}
        assert "2026-01-01" in actual_dates
        assert "2026-06-01" in actual_dates
        # 全月に ideal がある
        assert all(p["ideal"] is not None for p in result.chart)
        # 未来月には projected がある
        future_projected = [
            p for p in result.chart if cast("str", p["date"]) > "2026-06-01" and p["projected"] is not None
        ]
        assert len(future_projected) > 0

    def test_invalid_target_value_raises(self) -> None:
        """target_value=0 でも計算は動く（達成率0、ステータスunknown）"""
        goal = FinancialGoalEntity(
            id=1,
            user_id=1,
            name="x",
            target_value_jpy=Decimal("0"),
            target_date="2030-01-01",
            scope_type="family",
            created_at=datetime.datetime(2024, 1, 1),
        )
        members = [_make_member(1)]
        accounts = [_make_account(10, 1)]
        latest = [_make_snapshot(10, "2026-01-01", 5000000)]
        service = GoalProgressService()
        result = service.compute(goal, members, accounts, latest, list(latest), today=datetime.date(2026, 1, 15))
        assert result.achievement_rate_pct == Decimal("0")
        assert result.projection_status == "unknown"
