"""スクリーニングプリセットAPIビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class ScreeningPresetListView(APIView):
    """GET /api/stocks/screening/presets/ — 一覧
    POST /api/stocks/screening/presets/ — 作成"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        usecase = container.list_screening_presets_usecase()
        presets = usecase.execute(user_id=request.user.id)  # type: ignore[arg-type]
        return Response(
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "priority": p.priority,
                    "filters": p.filters,
                }
                for p in presets
            ]
        )

    def post(self, request: Request) -> Response:
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "name は必須です"}, status=status.HTTP_400_BAD_REQUEST)
        priority = int(request.data.get("priority", 0))
        filters = request.data.get("filters", {})

        usecase = container.save_screening_preset_usecase()
        preset = usecase.execute(
            user_id=cast("int", request.user.id),
            name=name,
            priority=priority,
            filters=filters,
        )
        return Response(
            {"id": preset.id, "name": preset.name, "priority": preset.priority, "filters": preset.filters},
            status=status.HTTP_201_CREATED,
        )


class ScreeningPresetDetailView(APIView):
    """PUT /api/stocks/screening/presets/{id}/ — 更新
    DELETE /api/stocks/screening/presets/{id}/ — 削除"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"detail": "name は必須です"}, status=status.HTTP_400_BAD_REQUEST)
        priority = int(request.data.get("priority", 0))
        filters = request.data.get("filters", {})

        usecase = container.save_screening_preset_usecase()
        preset = usecase.execute(
            user_id=cast("int", request.user.id),
            name=name,
            priority=priority,
            filters=filters,
            preset_id=pk,
        )
        return Response({"id": preset.id, "name": preset.name, "priority": preset.priority, "filters": preset.filters})

    def delete(self, request: Request, pk: int) -> Response:
        usecase = container.delete_screening_preset_usecase()
        deleted = usecase.execute(preset_id=pk, user_id=cast("int", request.user.id))
        if not deleted:
            return Response({"detail": "プリセットが見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
