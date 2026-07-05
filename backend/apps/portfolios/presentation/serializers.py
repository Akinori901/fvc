from typing import Any

from rest_framework import serializers

from apps.portfolios.models import FamilyMember, PortfolioAccount

# ============================================================
# 家族ポートフォリオ（新シリアライザー）
# ============================================================


class FamilyMemberSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=50)
    role = serializers.ChoiceField(choices=FamilyMember.Role.choices)
    role_display = serializers.SerializerMethodField()
    color_code = serializers.CharField(max_length=7, default="#1976d2")
    display_order = serializers.IntegerField(default=0)
    include_in_family_total = serializers.BooleanField(default=True)

    def get_role_display(self, obj: dict[str, Any]) -> str:
        return dict(FamilyMember.Role.choices).get(obj.get("role", ""), "")


class PortfolioAccountSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(read_only=True)
    family_member_id = serializers.IntegerField()
    family_member_name = serializers.CharField(read_only=True)
    institution = serializers.CharField(max_length=100)
    institution_type = serializers.ChoiceField(choices=PortfolioAccount.InstitutionType.choices)
    institution_type_display = serializers.SerializerMethodField()
    asset_class = serializers.ChoiceField(choices=PortfolioAccount.AssetClass.choices)
    asset_class_display = serializers.SerializerMethodField()
    trading_type = serializers.ChoiceField(choices=PortfolioAccount.TradingType.choices, default="spot")
    trading_type_display = serializers.SerializerMethodField()
    nickname = serializers.CharField(max_length=100, allow_blank=True, default="")
    currency = serializers.CharField(max_length=3, default="JPY")
    notes = serializers.CharField(allow_blank=True, default="")
    is_active = serializers.BooleanField(default=True)
    expected_return_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, required=False, default=None
    )
    margin_credit_type = serializers.ChoiceField(
        choices=PortfolioAccount.MarginCreditType.choices,
        allow_null=True,
        required=False,
        default=None,
    )
    margin_credit_type_display = serializers.SerializerMethodField()
    margin_interest_rate = serializers.DecimalField(
        max_digits=5, decimal_places=4, allow_null=True, required=False, default=None
    )

    def get_margin_credit_type_display(self, obj: Any) -> str:
        val: str | None = (
            obj.get("margin_credit_type") if isinstance(obj, dict) else getattr(obj, "margin_credit_type", None)
        )
        if val is None:
            return ""
        return dict(PortfolioAccount.MarginCreditType.choices).get(val, val)

    def get_institution_type_display(self, obj: Any) -> str:
        val: str = obj.get("institution_type", "") if isinstance(obj, dict) else getattr(obj, "institution_type", "")
        return dict(PortfolioAccount.InstitutionType.choices).get(val, val)

    def get_asset_class_display(self, obj: Any) -> str:
        val: str = obj.get("asset_class", "") if isinstance(obj, dict) else getattr(obj, "asset_class", "")
        return dict(PortfolioAccount.AssetClass.choices).get(val, val)

    def get_trading_type_display(self, obj: Any) -> str:
        val: str = obj.get("trading_type", "spot") if isinstance(obj, dict) else getattr(obj, "trading_type", "spot")
        return dict(PortfolioAccount.TradingType.choices).get(val, val)


class AccountHoldingSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(read_only=True)
    stock_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    ticker_code = serializers.CharField(allow_blank=True, default="")
    asset_name = serializers.CharField(max_length=255)
    asset_type = serializers.CharField(max_length=20)
    quantity = serializers.DecimalField(max_digits=16, decimal_places=4, allow_null=True, required=False)
    unit_price = serializers.DecimalField(max_digits=16, decimal_places=4, allow_null=True, required=False)
    value_jpy = serializers.DecimalField(max_digits=16, decimal_places=0)
    cost_jpy = serializers.DecimalField(max_digits=16, decimal_places=0, allow_null=True, required=False)
    built_date = serializers.DateField(allow_null=True, required=False, default=None)


class AccountSnapshotSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(read_only=True)
    account_id = serializers.IntegerField(read_only=True)
    snapshot_date = serializers.DateField()
    total_value_jpy = serializers.DecimalField(max_digits=16, decimal_places=0)
    total_cost_jpy = serializers.DecimalField(max_digits=16, decimal_places=0, allow_null=True, required=False)
    exchange_rate = serializers.DecimalField(max_digits=10, decimal_places=4, allow_null=True, required=False)
    notes = serializers.CharField(allow_blank=True, default="")
    holdings = AccountHoldingSerializer(many=True, required=False, default=list)


class WatchlistItemSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField(read_only=True)
    stock_code = serializers.CharField()
    stock_name = serializers.CharField(read_only=True)
    memo = serializers.CharField(required=False, allow_blank=True, default="")
