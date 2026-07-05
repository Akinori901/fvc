"""MCP API キー管理 View（一覧 / 発行 / 失効）。

既存セッション認証（dj-rest-auth JWT）でログイン中のユーザーが自分のキーを管理する。
MCP キー認証は使わない（自分の MCP キーを発行する画面なので）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.mcp.presentation.serializers import (
    ApiKeySummarySerializer,
    IssueApiKeyRequestSerializer,
    IssuedApiKeyResponseSerializer,
)
from config import container

from ...domain.exceptions import McpApiKeyNotFoundError

if TYPE_CHECKING:
    from rest_framework.request import Request


class McpApiKeyListIssueView(APIView):
    """GET (一覧) / POST (発行)。"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.list_api_keys_usecase()
        items = usecase.execute(user_id=request.user.id)
        return Response(
            {
                "count": len(items),
                "items": ApiKeySummarySerializer(items, many=True).data,
            }
        )

    def post(self, request: Request) -> Response:
        serializer = IssueApiKeyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert isinstance(request.user.id, int)
        usecase = container.issue_api_key_usecase()
        issued = usecase.execute(
            user_id=request.user.id,
            label=serializer.validated_data["label"],
        )
        return Response(
            IssuedApiKeyResponseSerializer(issued).data,
            status=status.HTTP_201_CREATED,
        )


class McpApiKeyRevokeView(APIView):
    """DELETE 失効。"""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, key_id: int) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.revoke_api_key_usecase()
        try:
            usecase.execute(key_id=key_id, user_id=request.user.id)
        except McpApiKeyNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
