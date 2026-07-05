"""Admin: 許可 email 追加 / 削除 View。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_cognito.application.dto import AddAllowedEmailDTO
from apps.auth_cognito.presentation.serializers.admin_serializers import (
    AddAllowedEmailSerializer,
    UserAllowedEmailInfoSerializer,
)
from apps.core.permissions import IsSuperUser
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class AdminAllowedEmailCreateView(APIView):
    """`POST /api/admin/users/{user_id}/allowed-emails/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def post(self, request: Request, user_id: int) -> Response:
        serializer = AddAllowedEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usecase = container.add_allowed_email_usecase()
        try:
            info = usecase.execute(
                AddAllowedEmailDTO(
                    user_id=user_id,
                    email=serializer.validated_data["email"],
                    label=serializer.validated_data.get("label", ""),
                )
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            UserAllowedEmailInfoSerializer({"id": info.id, "email": info.email, "label": info.label}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminAllowedEmailDestroyView(APIView):
    """`DELETE /api/admin/users/{user_id}/allowed-emails/{allowed_id}/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def delete(self, request: Request, user_id: int, allowed_id: int) -> Response:
        usecase = container.remove_allowed_email_usecase()
        try:
            usecase.execute(allowed_id=allowed_id, user_id=user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
