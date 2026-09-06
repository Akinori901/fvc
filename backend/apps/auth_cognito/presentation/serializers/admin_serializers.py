"""Admin 管理 API シリアライザー。

DTO (AdminUserRow / CreateAdminUserDTO / AddAllowedEmailDTO 等)
を REST で受け渡すための入出力ラッパー。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import serializers

if TYPE_CHECKING:
    from apps.auth_cognito.application.dto import (
        AdminUserRow,
        CognitoLinkInfo,
        UserAllowedEmailInfo,
    )


class CognitoLinkInfoSerializer(serializers.Serializer):  # type: ignore[type-arg]
    id = serializers.IntegerField()
    cognito_sub = serializers.CharField()
    provider = serializers.CharField()
    cognito_email = serializers.CharField(allow_blank=True)
    last_signed_in_at = serializers.DateTimeField(allow_null=True)


class UserAllowedEmailInfoSerializer(serializers.Serializer):  # type: ignore[type-arg]
    id = serializers.IntegerField()
    email = serializers.CharField()
    label = serializers.CharField(allow_blank=True)  # type: ignore[assignment]


class AdminUserRowSerializer(serializers.Serializer):  # type: ignore[type-arg]
    id = serializers.IntegerField()
    email = serializers.CharField(allow_blank=True)
    username = serializers.CharField()
    is_superuser = serializers.BooleanField()
    is_staff = serializers.BooleanField()
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    last_login = serializers.DateTimeField(allow_null=True)
    cognito_links = CognitoLinkInfoSerializer(many=True)
    allowed_emails = UserAllowedEmailInfoSerializer(many=True)

    @classmethod
    def from_row(cls, row: AdminUserRow) -> dict[str, Any]:
        return {
            "id": row.id,
            "email": row.email,
            "username": row.username,
            "is_superuser": row.is_superuser,
            "is_staff": row.is_staff,
            "is_active": row.is_active,
            "date_joined": row.date_joined,
            "last_login": row.last_login,
            "cognito_links": [_link_to_dict(link) for link in row.cognito_links],
            "allowed_emails": [_allowed_to_dict(allowed) for allowed in row.allowed_emails],
        }


class CreateAdminUserSerializer(serializers.Serializer):  # type: ignore[type-arg]
    email = serializers.EmailField(max_length=254)


class AddAllowedEmailSerializer(serializers.Serializer):  # type: ignore[type-arg]
    email = serializers.EmailField(max_length=254)
    label = serializers.CharField(  # type: ignore[assignment]
        max_length=100, required=False, allow_blank=True, default=""
    )


def _link_to_dict(link: CognitoLinkInfo) -> dict[str, Any]:
    return {
        "id": link.id,
        "cognito_sub": link.cognito_sub,
        "provider": link.provider,
        "cognito_email": link.cognito_email,
        "last_signed_in_at": link.last_signed_in_at,
    }


def _allowed_to_dict(allowed: UserAllowedEmailInfo) -> dict[str, Any]:
    return {
        "id": allowed.id,
        "email": allowed.email,
        "label": allowed.label,
    }
