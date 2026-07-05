"""目標CRUD View。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.domain.exceptions import (
    DuplicateScopeError,
    GoalNotFoundError,
    InvalidGoalError,
)
from apps.goals.presentation.serializers import FinancialGoalSerializer
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.goals.domain.entities import FinancialGoalEntity


def _goal_to_dict(g: FinancialGoalEntity) -> dict[str, Any]:
    return {
        "id": g.id,
        "name": g.name,
        "target_value_jpy": str(g.target_value_jpy),
        "target_date": g.target_date,
        "scope_type": g.scope_type,
        "member_ids": g.member_ids,
        "is_active": g.is_active,
        "display_order": g.display_order,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }


class GoalListView(APIView):
    """GET /api/goals/  POST /api/goals/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        usecase = container.goals_list_usecase()
        user_id = cast("int", request.user.pk)
        goals = usecase.execute(user_id)
        return Response([_goal_to_dict(g) for g in goals])

    def post(self, request: Request) -> Response:
        serializer = FinancialGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        usecase = container.goals_save_usecase()
        user_id = cast("int", request.user.pk)
        try:
            saved = usecase.execute(
                user_id=user_id,
                name=d["name"],
                target_value_jpy=Decimal(d["target_value_jpy"]),
                target_date=str(d["target_date"]),
                scope_type=d["scope_type"],
                member_ids=d.get("member_ids", []) or [],
            )
        except DuplicateScopeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except InvalidGoalError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_goal_to_dict(saved), status=status.HTTP_201_CREATED)


class GoalDetailView(APIView):
    """PUT/DELETE /api/goals/<id>/"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        serializer = FinancialGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        usecase = container.goals_save_usecase()
        user_id = cast("int", request.user.pk)
        try:
            saved = usecase.execute(
                user_id=user_id,
                name=d["name"],
                target_value_jpy=Decimal(d["target_value_jpy"]),
                target_date=str(d["target_date"]),
                scope_type=d["scope_type"],
                member_ids=d.get("member_ids", []) or [],
                goal_id=pk,
            )
        except DuplicateScopeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except InvalidGoalError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_goal_to_dict(saved))

    def delete(self, request: Request, pk: int) -> Response:
        usecase = container.goals_delete_usecase()
        user_id = cast("int", request.user.pk)
        try:
            usecase.execute(pk, user_id)
        except GoalNotFoundError:
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
