from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.goals.domain.repositories import FinancialGoalRepository


class ReorderGoalsUseCase:
    """目標カードの並び替え。"""

    def __init__(self, repo: FinancialGoalRepository) -> None:
        self._repo = repo

    def execute(self, user_id: int, ordered_ids: list[int]) -> None:
        self._repo.reorder(user_id, ordered_ids)
