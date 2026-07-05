"""AI機能シリアライザー。"""

from __future__ import annotations

from rest_framework import serializers

VALID_QUESTION_TYPES = [
    "pbr_low",
    "investment_risk",
    "growth_outlook",
    "custom",
    "price_forecast",
    "price_drop_reason",
    "dividend_analysis",
    "sector_comparison",
]
VALID_EXPERT_ROLES = [
    "general",
    "quant",
    "fundamental",
    "macro",
    "technical",
    "risk_mgmt",
]
VALID_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
]


class AiConfigSerializer(serializers.Serializer):  # type: ignore[type-arg]
    api_key = serializers.CharField(required=False, allow_blank=True, max_length=500)
    model = serializers.ChoiceField(
        choices=VALID_MODELS,
        default="gemini-2.5-flash",
        required=False,
    )
    is_enabled = serializers.BooleanField(required=False, default=False)


class AnalyzeRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    question_type = serializers.ChoiceField(choices=VALID_QUESTION_TYPES)
    custom_question = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        default="",
    )
    expert_role = serializers.ChoiceField(
        choices=VALID_EXPERT_ROLES,
        required=False,
        default="general",
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        custom_q = str(attrs.get("custom_question", ""))
        if attrs.get("question_type") == "custom" and not custom_q.strip():
            raise serializers.ValidationError(
                {"custom_question": "question_typeがcustomの場合はcustom_questionは必須です。"}
            )
        return attrs
