"""目標進捗 View。"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.goals.domain.exceptions import GoalNotFoundError
from apps.goals.presentation.views.goal_views import _goal_to_dict
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class GoalProgressView(APIView):
    """GET /api/goals/<id>/progress/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        usecase = container.goals_progress_usecase()
        user_id = cast("int", request.user.pk)
        try:
            goal, result = usecase.execute(pk, user_id)
        except GoalNotFoundError:
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "goal": _goal_to_dict(goal),
                "current_value_jpy": str(result.current_value_jpy),
                "achievement_rate_pct": str(result.achievement_rate_pct),
                "ideal_value_now_jpy": str(result.ideal_value_now_jpy),
                "gap_jpy": str(result.gap_jpy),
                "avg_monthly_increase_jpy": (
                    str(result.avg_monthly_increase_jpy) if result.avg_monthly_increase_jpy is not None else None
                ),
                "projected_value_at_target_jpy": (
                    str(result.projected_value_at_target_jpy)
                    if result.projected_value_at_target_jpy is not None
                    else None
                ),
                "projection_status": result.projection_status,
                "chart": result.chart,
            }
        )
