from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.goals.domain.entities import FinancialGoalEntity
    from apps.goals.domain.repositories import FinancialGoalRepository


class ListGoalsUseCase:
    def __init__(self, repo: FinancialGoalRepository) -> None:
        self._repo = repo

    def execute(self, user_id: int) -> list[FinancialGoalEntity]:
        return self._repo.find_by_user(user_id)
