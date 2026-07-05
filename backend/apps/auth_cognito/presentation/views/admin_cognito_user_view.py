"""Admin: Cognito User Pool 一覧 + disable/enable/delete View。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_cognito.presentation.serializers.admin_serializers import (
    CognitoUserRowSerializer,
)
from apps.core.permissions import IsSuperUser
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class AdminCognitoUserListView(APIView):
    """`GET /api/admin/cognito-users/` — Cognito User Pool 一覧 + 紐付き状況."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request: Request) -> Response:
        usecase = container.list_cognito_users_usecase()
        rows = usecase.execute()
        return Response({"users": [CognitoUserRowSerializer.from_row(row) for row in rows]})


class AdminCognitoUserDisableView(APIView):
    """`POST /api/admin/cognito-users/{username}/disable/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, username: str) -> Response:
        usecase = container.disable_cognito_user_usecase()
        try:
            usecase.execute(username)
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCognitoUserEnableView(APIView):
    """`POST /api/admin/cognito-users/{username}/enable/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, username: str) -> Response:
        usecase = container.enable_cognito_user_usecase()
        try:
            usecase.execute(username)
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCognitoUserDestroyView(APIView):
    """`DELETE /api/admin/cognito-users/{username}/` — Cognito 削除 + link 同期削除."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def delete(self, request: Request, username: str) -> Response:
        usecase = container.delete_cognito_user_usecase()
        try:
            usecase.execute(username)
        except Exception as exc:  # noqa: BLE001
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
