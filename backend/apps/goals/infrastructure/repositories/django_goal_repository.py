"""金融目標リポジトリ Django実装。"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Max

from apps.goals.domain.entities import FinancialGoalEntity
from apps.goals.domain.repositories import FinancialGoalRepository
from apps.goals.models import FinancialGoal, GoalMember


class DjangoFinancialGoalRepository(FinancialGoalRepository):
    def find_by_user(self, user_id: int) -> list[FinancialGoalEntity]:
        qs = (
            FinancialGoal.objects.filter(user_id=user_id, is_active=True)
            .prefetch_related("member_links")
            .order_by("display_order", "id")
        )
        return [self._to_entity(g) for g in qs]

    def find_by_id(self, goal_id: int, user_id: int) -> FinancialGoalEntity | None:
        obj = (
            FinancialGoal.objects.filter(pk=goal_id, user_id=user_id, is_active=True)
            .prefetch_related("member_links")
            .first()
        )
        return self._to_entity(obj) if obj else None

    def find_family_goal(self, user_id: int) -> FinancialGoalEntity | None:
        obj = (
            FinancialGoal.objects.filter(user_id=user_id, scope_type="family", is_active=True)
            .prefetch_related("member_links")
            .first()
        )
        return self._to_entity(obj) if obj else None

    def find_member_combo_goal(self, user_id: int, member_ids: list[int]) -> FinancialGoalEntity | None:
        target_set = frozenset(member_ids)
        candidates = FinancialGoal.objects.filter(
            user_id=user_id, scope_type="members", is_active=True
        ).prefetch_related("member_links")
        for g in candidates:
            existing = frozenset(link.family_member_id for link in g.member_links.all())
            if existing == target_set:
                return self._to_entity(g)
        return None

    @transaction.atomic
    def save(self, entity: FinancialGoalEntity) -> FinancialGoalEntity:
        if entity.id is not None:
            obj = FinancialGoal.objects.get(pk=entity.id, user_id=entity.user_id)
            obj.name = entity.name
            obj.target_value_jpy = entity.target_value_jpy
            obj.target_date = entity.target_date
            obj.scope_type = entity.scope_type
            obj.is_active = entity.is_active
            obj.save()
        else:
            # 新規追加時は末尾に配置
            max_order = FinancialGoal.objects.filter(user_id=entity.user_id).aggregate(m=Max("display_order"))["m"]
            next_order = (max_order + 1) if max_order is not None else 0
            obj = FinancialGoal.objects.create(
                user_id=entity.user_id,
                name=entity.name,
                target_value_jpy=entity.target_value_jpy,
                target_date=entity.target_date,
                scope_type=entity.scope_type,
                is_active=entity.is_active,
                display_order=next_order,
            )

        # メンバーリンク再構築
        GoalMember.objects.filter(goal=obj).delete()
        if entity.scope_type == "members":
            for mid in entity.member_ids:
                GoalMember.objects.create(goal=obj, family_member_id=mid)

        return self._to_entity(obj)

    def delete(self, goal_id: int, user_id: int) -> None:
        FinancialGoal.objects.filter(pk=goal_id, user_id=user_id).delete()

    @transaction.atomic
    def reorder(self, user_id: int, ordered_ids: list[int]) -> None:
        """渡された ID 順に display_order を 0,1,2... で再割当する。

        - ユーザー所有の目標のみ対象
        - 渡されなかった目標は末尾にまとめて配置
        """
        owned_ids = set(FinancialGoal.objects.filter(user_id=user_id).values_list("id", flat=True))
        seen: set[int] = set()
        order = 0
        for goal_id in ordered_ids:
            if goal_id in owned_ids and goal_id not in seen:
                FinancialGoal.objects.filter(pk=goal_id, user_id=user_id).update(display_order=order)
                seen.add(goal_id)
                order += 1
        # 渡されなかった既存目標は末尾に
        for remaining_id in owned_ids - seen:
            FinancialGoal.objects.filter(pk=remaining_id, user_id=user_id).update(display_order=order)
            order += 1

    def _to_entity(self, obj: FinancialGoal) -> FinancialGoalEntity:
        member_ids = [link.family_member_id for link in obj.member_links.all()]
        return FinancialGoalEntity(
            id=obj.pk,
            user_id=obj.user_id,
            name=obj.name,
            target_value_jpy=obj.target_value_jpy,
            target_date=str(obj.target_date),
            scope_type=obj.scope_type,
            member_ids=member_ids,
            is_active=obj.is_active,
            display_order=obj.display_order,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
