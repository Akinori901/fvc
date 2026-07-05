"""共通 DRF Permission クラス。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class IsSuperUser(BasePermission):
    """`request.user.is_superuser` のみを通す。

    管理者専用 API (`/api/admin/*`) で使用する。
    `IsAuthenticated` と組み合わせて使うことを想定。
    """

    message = "管理者権限が必要です"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))
