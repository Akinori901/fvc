from rest_framework import serializers


class CalculateFairValueSerializer(serializers.Serializer):  # type: ignore[type-arg]
    stock_code = serializers.CharField(max_length=10)
    growth_rate = serializers.DecimalField(max_digits=8, decimal_places=4)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class ReverseCalculateSerializer(serializers.Serializer):  # type: ignore[type-arg]
    stock_code = serializers.CharField(max_length=10)
    current_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
