"""共通 View モジュール。

Cognito OAuth 移行 (Phase D) 以後、dj-rest-auth に依存しない自前の
`UserDetailsView` を提供する。フロントエンド (`auth-hub-listener.ts` と
`ProtectedRoute`) は Cognito ログイン後にこの View を叩き、Django User の
基本情報 (pk / username / email / first_name / last_name / is_superuser) を
取得して `authStore` に保存する。

認証は `CognitoJWTAuthentication` (`apps.auth_cognito.presentation.
drf_authentication`) が DRF 認証クラスとして適用される。
"""

from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated


class _UserDetailsSerializer(serializers.ModelSerializer[User]):
    """`/api/auth/user/` のレスポンス serializer。"""

    class Meta:
        model = User
        fields = ("pk", "username", "email", "first_name", "last_name", "is_superuser")
        read_only_fields = fields


class UserDetailsView(RetrieveAPIView[User]):
    """`GET /api/auth/user/` — 認証済みユーザーの情報を返す。

    旧 `dj_rest_auth.views.UserDetailsView` の差し替え。
    `request.user` を返すだけのシンプルな構造で、Cognito JIT provisioning
    で解決された Django User がそのまま返される。
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = _UserDetailsSerializer

    def get_object(self) -> User:
        return self.request.user  # type: ignore[return-value]
