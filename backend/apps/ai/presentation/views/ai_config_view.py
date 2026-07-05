"""AI設定 GET/PUT ビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.presentation.serializers import AiConfigSerializer
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class AiConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        usecase = container.get_ai_config_usecase()
        assert isinstance(request.user.id, int)
        result = usecase.execute(user_id=request.user.id)
        return Response(
            {
                "provider": result.provider,
                "model": result.model,
                "is_enabled": result.is_enabled,
                "has_api_key": result.has_api_key,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None,
            }
        )

    def put(self, request: Request) -> Response:
        serializer = AiConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usecase = container.save_ai_config_usecase()
        assert isinstance(request.user.id, int)
        result = usecase.execute(
            user_id=request.user.id,
            provider="gemini",
            api_key=serializer.validated_data.get("api_key"),
            model=serializer.validated_data.get("model", "gemini-2.5-flash"),
            is_enabled=serializer.validated_data.get("is_enabled", False),
        )
        return Response(
            {
                "provider": result.provider,
                "model": result.model,
                "is_enabled": result.is_enabled,
                "has_api_key": result.has_api_key,
                "updated_at": result.updated_at.isoformat() if result.updated_at else None,
            }
        )
