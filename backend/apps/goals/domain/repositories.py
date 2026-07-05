"""目標管理リポジトリABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import FinancialGoalEntity


class FinancialGoalRepository(ABC):
    @abstractmethod
    def find_by_user(self, user_id: int) -> list[FinancialGoalEntity]: ...

    @abstractmethod
    def find_by_id(self, goal_id: int, user_id: int) -> FinancialGoalEntity | None: ...

    @abstractmethod
    def find_family_goal(self, user_id: int) -> FinancialGoalEntity | None:
        """家族合計スコープの目標（user毎に最大1つ）"""
        ...

    @abstractmethod
    def find_member_combo_goal(self, user_id: int, member_ids: list[int]) -> FinancialGoalEntity | None:
        """完全一致するメンバー組み合わせの目標"""
        ...

    @abstractmethod
    def save(self, entity: FinancialGoalEntity) -> FinancialGoalEntity: ...

    @abstractmethod
    def delete(self, goal_id: int, user_id: int) -> None: ...

    @abstractmethod
    def reorder(self, user_id: int, ordered_ids: list[int]) -> None:
        """渡された ID 順に display_order を 0,1,2... で再割当する"""
        ...
