"""仮想売買シリアライザー。"""

from __future__ import annotations

from rest_framework import serializers

VALID_TRADE_TYPES = ["buy", "sell"]


class ExecuteTradeSerializer(serializers.Serializer):  # type: ignore[type-arg]
    stock_code = serializers.CharField(max_length=10)
    trade_type = serializers.ChoiceField(choices=VALID_TRADE_TYPES)
    quantity = serializers.IntegerField(min_value=100)
    memo = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")

    def validate_quantity(self, value: int) -> int:
        if value % 100 != 0:
            raise serializers.ValidationError("数量は100株単位で入力してください。")
        return value
