"""目標管理シリアライザ。"""

from rest_framework import serializers


class FinancialGoalSerializer(serializers.Serializer):  # type: ignore[type-arg]
    name = serializers.CharField(max_length=100)
    target_value_jpy = serializers.DecimalField(max_digits=16, decimal_places=0)
    target_date = serializers.DateField()
    scope_type = serializers.ChoiceField(choices=[("family", "family"), ("members", "members")])
    member_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
