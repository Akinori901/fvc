"""共通 DRF Permission クラス。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

from apps.core.services import central_authz

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class IsSuperUser(BasePermission):
    """管理者だけを通す。

    管理者専用 API (`/api/admin/*`) で使用する。
    `IsAuthenticated` と組み合わせて使うことを想定。

    判定は **中央（認証コンソール）と既存の `is_superuser` の
    どちらかで許可されれば通す**。

    ロールの管理を認証コンソールの画面に寄せつつ、中央が落ちても
    既存ユーザーが管理画面から締め出されないようにするため。
    中央だけで判定するのは、運用が安定してから。
    """

    message = "管理者権限が必要です"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False

        # 中央が admin と言えば通す。
        # 中央が判断できない（未設定・障害）場合は None が返るので、
        # 下の既存判定に落ちる。**中央の拒否だけで締め出さない。**
        central = central_authz.fetch(getattr(user, "email", ""))
        if central is not None and central.allowed and central.is_admin:
            return True

        return bool(getattr(user, "is_superuser", False))
