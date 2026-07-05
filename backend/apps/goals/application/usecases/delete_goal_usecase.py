from __future__ import annotations

from typing import TYPE_CHECKING

from apps.goals.domain.exceptions import GoalNotFoundError

if TYPE_CHECKING:
    from apps.goals.domain.repositories import FinancialGoalRepository


class DeleteGoalUseCase:
    def __init__(self, repo: FinancialGoalRepository) -> None:
        self._repo = repo

    def execute(self, goal_id: int, user_id: int) -> None:
        existing = self._repo.find_by_id(goal_id, user_id)
        if existing is None:
            raise GoalNotFoundError(f"id={goal_id}")
        self._repo.delete(goal_id, user_id)
