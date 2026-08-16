"""Admin: auth_user 一覧 + 作成 View。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_cognito.application.dto import CreateAdminUserDTO
from apps.auth_cognito.presentation.serializers.admin_serializers import (
    AdminUserRowSerializer,
    CreateAdminUserSerializer,
)
from apps.core.permissions import IsSuperUser
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class AdminUserListCreateView(APIView):
    """`GET/POST /api/admin/users/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def get(self, request: Request) -> Response:
        usecase = container.list_admin_users_usecase()
        rows = usecase.execute()
        return Response({"users": [AdminUserRowSerializer.from_row(row) for row in rows]})

    def post(self, request: Request) -> Response:
        serializer = CreateAdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usecase = container.create_admin_user_usecase()
        try:
            row = usecase.execute(CreateAdminUserDTO(email=serializer.validated_data["email"]))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            AdminUserRowSerializer.from_row(row),
            status=status.HTTP_201_CREATED,
        )


class AdminUserDestroyView(APIView):
    """`DELETE /api/admin/users/{user_id}/` — auth_user 完全削除 (CASCADE)。

    self-delete はガード (自分自身を削除すると admin がいなくなって不可逆)。
    """

    permission_classes = [IsAuthenticated, IsSuperUser]

    def delete(self, request: Request, user_id: int) -> Response:
        if request.user.id == user_id:
            return Response(
                {"detail": "自分自身を削除することはできません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usecase = container.delete_admin_user_usecase()
        try:
            usecase.execute(user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserDisableView(APIView):
    """`POST /api/admin/users/{user_id}/disable/` — is_active=False。"""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, user_id: int) -> Response:
        if request.user.id == user_id:
            return Response(
                {"detail": "自分自身を無効化することはできません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usecase = container.disable_admin_user_usecase()
        try:
            usecase.execute(user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserEnableView(APIView):
    """`POST /api/admin/users/{user_id}/enable/` — is_active=True。"""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, user_id: int) -> Response:
        usecase = container.enable_admin_user_usecase()
        try:
            usecase.execute(user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminUserResendInviteView(APIView):
    """`POST /api/admin/users/{user_id}/resend-invite/` — 招待メールを再送する。"""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, user_id: int) -> Response:
        usecase = container.resend_invite_usecase()
        try:
            usecase.execute(user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
