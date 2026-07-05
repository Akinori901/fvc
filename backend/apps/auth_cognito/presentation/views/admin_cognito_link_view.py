"""Admin: Cognito link 削除 View。

Google アカウント差し替え等で「auth_user に紐付いた古い sub」を消すための用途。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSuperUser
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class AdminCognitoLinkDestroyView(APIView):
    """`DELETE /api/admin/users/{user_id}/cognito-links/{link_id}/`."""

    permission_classes = [IsAuthenticated, IsSuperUser]

    def delete(self, request: Request, user_id: int, link_id: int) -> Response:
        usecase = container.delete_cognito_link_usecase()
        try:
            usecase.execute(link_id=link_id, user_id=user_id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
