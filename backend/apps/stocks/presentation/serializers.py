from rest_framework import serializers

from ..models import Stock, StockFinancial, StockPrice


class StockSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = Stock
        fields = ["id", "code", "name", "market", "sector", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockFinancialSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = StockFinancial
        fields = ["id", "stock", "fiscal_year", "bps", "eps", "roe", "net_assets", "total_shares", "created_at"]
        read_only_fields = ["id", "created_at"]


class StockFinancialCreateSerializer(serializers.Serializer):  # type: ignore[type-arg]
    fiscal_year = serializers.IntegerField(min_value=1900, max_value=2100)
    bps = serializers.DecimalField(max_digits=12, decimal_places=2)
    eps = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    roe = serializers.DecimalField(max_digits=8, decimal_places=4, required=False, allow_null=True)
    net_assets = serializers.IntegerField(required=False, allow_null=True)
    total_shares = serializers.IntegerField(required=False, allow_null=True)


class StockPriceSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = StockPrice
        fields = ["id", "stock", "date", "close_price", "pbr", "volume", "created_at"]
        read_only_fields = ["id", "created_at"]
