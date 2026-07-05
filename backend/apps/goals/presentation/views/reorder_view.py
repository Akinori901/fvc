"""目標並び替え View。"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class GoalReorderView(APIView):
    """PUT /api/goals/reorder/  body: {"ordered_ids": [3, 1, 2]}"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request) -> Response:
        ordered_ids = request.data.get("ordered_ids")
        if not isinstance(ordered_ids, list) or not all(isinstance(x, int) for x in ordered_ids):
            return Response(
                {"detail": "ordered_ids は整数の配列で指定してください"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        usecase = container.goals_reorder_usecase()
        user_id = cast("int", request.user.pk)
        usecase.execute(user_id, ordered_ids)
        return Response(status=status.HTTP_204_NO_CONTENT)
