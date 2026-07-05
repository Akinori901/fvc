"""AI機能URLルーティング。"""

from django.urls import path

from apps.ai.presentation.views.ai_config_view import AiConfigView
from apps.ai.presentation.views.analyze_view import StockAnalyzeView

urlpatterns = [
    path("ai/config/", AiConfigView.as_view(), name="ai-config"),
    path("ai/stocks/<str:code>/analyze/", StockAnalyzeView.as_view(), name="ai-stock-analyze"),
]
