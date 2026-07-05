"""MCP / 外部AI連携 シリアライザー。"""

from __future__ import annotations

from rest_framework import serializers


class IssueApiKeyRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    label = serializers.CharField(required=True, max_length=100)  # type: ignore[assignment]


class ApiKeySummarySerializer(serializers.Serializer):  # type: ignore[type-arg]
    id = serializers.IntegerField()
    label = serializers.CharField()  # type: ignore[assignment]
    key_prefix = serializers.CharField()
    is_active = serializers.BooleanField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class IssuedApiKeyResponseSerializer(serializers.Serializer):  # type: ignore[type-arg]
    id = serializers.IntegerField()
    label = serializers.CharField()  # type: ignore[assignment]
    key_prefix = serializers.CharField()
    plain_key = serializers.CharField()
    created_at = serializers.DateTimeField()
