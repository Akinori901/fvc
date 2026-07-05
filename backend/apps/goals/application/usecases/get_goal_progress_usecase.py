from __future__ import annotations

from typing import TYPE_CHECKING

from apps.goals.domain.exceptions import GoalNotFoundError

if TYPE_CHECKING:
    from apps.goals.application.services.goal_progress_service import (
        GoalProgressResult,
        GoalProgressService,
    )
    from apps.goals.domain.entities import FinancialGoalEntity
    from apps.goals.domain.repositories import FinancialGoalRepository
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        FamilyMemberRepository,
        PortfolioAccountRepository,
    )


class GetGoalProgressUseCase:
    """目標進捗取得。

    リポジトリから必要データをロードし、GoalProgressService に委譲。
    """

    def __init__(
        self,
        goal_repo: FinancialGoalRepository,
        member_repo: FamilyMemberRepository,
        account_repo: PortfolioAccountRepository,
        snapshot_repo: AccountSnapshotRepository,
        service: GoalProgressService,
    ) -> None:
        self._goal_repo = goal_repo
        self._member_repo = member_repo
        self._account_repo = account_repo
        self._snapshot_repo = snapshot_repo
        self._service = service

    def execute(self, goal_id: int, user_id: int) -> tuple[FinancialGoalEntity, GoalProgressResult]:
        goal = self._goal_repo.find_by_id(goal_id, user_id)
        if goal is None:
            raise GoalNotFoundError(f"id={goal_id}")
        members = self._member_repo.find_by_user(user_id)
        accounts = self._account_repo.find_by_user(user_id)
        latest_snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        all_snapshots = self._snapshot_repo.find_all_by_user(user_id)
        result = self._service.compute(goal, members, accounts, latest_snapshots, all_snapshots)
        return goal, result
