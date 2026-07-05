from __future__ import annotations

from typing import TYPE_CHECKING

from apps.goals.domain.entities import FinancialGoalEntity
from apps.goals.domain.exceptions import DuplicateScopeError, InvalidGoalError

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.goals.domain.repositories import FinancialGoalRepository


class SaveGoalUseCase:
    """目標の作成・更新。

    重複スコープチェック:
      - scope_type="family" は user毎に1つのみ。既存があれば DuplicateScopeError
      - scope_type="members" はメンバーIDセットが完全一致する既存があれば同上
      - 自分自身を更新する場合は重複に該当しない
    """

    def __init__(self, repo: FinancialGoalRepository) -> None:
        self._repo = repo

    def execute(
        self,
        user_id: int,
        name: str,
        target_value_jpy: Decimal,
        target_date: str,
        scope_type: str,
        member_ids: list[int],
        goal_id: int | None = None,
    ) -> FinancialGoalEntity:
        if target_value_jpy <= 0:
            raise InvalidGoalError("目標金額は0より大きい必要があります")
        if scope_type not in ("family", "members"):
            raise InvalidGoalError("scope_type は family または members")
        if scope_type == "members" and not member_ids:
            raise InvalidGoalError("メンバー指定の目標には少なくとも1人のメンバーが必要です")

        # 重複チェック
        if scope_type == "family":
            existing = self._repo.find_family_goal(user_id)
            if existing and existing.id != goal_id:
                raise DuplicateScopeError("家族合計の目標は既に存在します")
        else:
            existing = self._repo.find_member_combo_goal(user_id, member_ids)
            if existing and existing.id != goal_id:
                raise DuplicateScopeError("同じメンバー組み合わせの目標は既に存在します")

        entity = FinancialGoalEntity(
            id=goal_id,
            user_id=user_id,
            name=name,
            target_value_jpy=target_value_jpy,
            target_date=target_date,
            scope_type=scope_type,
            member_ids=member_ids if scope_type == "members" else [],
        )
        return self._repo.save(entity)
