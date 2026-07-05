"""FX分析 URL 設定。"""

from django.urls import path

from .views.fx_analysis_view import FxAnalysisView

urlpatterns = [
    path("fx/analysis/", FxAnalysisView.as_view(), name="fx-analysis"),
]
