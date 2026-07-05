"""チャット API の DRF Serializer。"""

from __future__ import annotations

from rest_framework import serializers


class SendMessageRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """POST /api/chat/messages/ のリクエストボディ。"""

    user_message = serializers.CharField(required=True, allow_blank=False, max_length=4000)
    session_id = serializers.IntegerField(required=False, allow_null=True)
    use_admin_key = serializers.BooleanField(required=False, default=False)
