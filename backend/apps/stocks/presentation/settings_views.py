"""設定APIビュー。"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSuperUser
from apps.stocks.models import ApiConfig

# J-Quantsプラン別の機能マッピング
PLAN_FEATURES = {
    "free": {
        "label": "Free",
        "stock_list_sync": True,
        "financial_sync": False,
        "financial_years": 0,
        "price_sync": False,
        "manual_calculation": True,
    },
    "light": {
        "label": "Light",
        "stock_list_sync": True,
        "financial_sync": True,
        "financial_years": 2,
        "price_sync": False,
        "manual_calculation": True,
    },
    "standard": {
        "label": "Standard",
        "stock_list_sync": True,
        "financial_sync": True,
        "financial_years": 10,
        "price_sync": True,
        "manual_calculation": True,
    },
    "premium": {
        "label": "Premium",
        "stock_list_sync": True,
        "financial_sync": True,
        "financial_years": -1,  # unlimited
        "price_sync": True,
        "manual_calculation": True,
    },
}


class ApiConfigListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        configs = ApiConfig.objects.all()
        result = []
        for config in configs:
            plan = config.plan or "free"
            features = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
            result.append(
                {
                    "provider": config.provider,
                    "is_enabled": config.is_enabled,
                    "plan": plan,
                    "plan_features": features,
                }
            )
        return Response(result)


class ApiConfigDetailView(APIView):
    # APIキーの書き換えは管理者のみに限定する
    permission_classes = [IsSuperUser]

    def put(self, request: Request, provider: str) -> Response:
        try:
            config = ApiConfig.objects.get(provider=provider)
        except ApiConfig.DoesNotExist:
            config = ApiConfig(provider=provider)

        if "api_key" in request.data:
            config.api_key = request.data["api_key"]
        if "plan" in request.data:
            config.plan = request.data["plan"]
        if "is_enabled" in request.data:
            config.is_enabled = request.data["is_enabled"]

        config.save()

        plan = config.plan or "free"
        features = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"])
        return Response(
            {
                "provider": config.provider,
                "is_enabled": config.is_enabled,
                "plan": plan,
                "plan_features": features,
            }
        )
