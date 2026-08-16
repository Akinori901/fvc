from django.urls import path

from . import views
from .etf_views import EtfListView
from .financial_reset_view import FinancialResetView
from .manual_financial_views import ManualFinancialDetailView, ManualFinancialListView
from .margin_views import StockMarginView
from .recommendation_views import RecommendationsView
from .reit_views import ReitListView
from .screening_preset_views import ScreeningPresetDetailView, ScreeningPresetListView
from .screening_views import ScreeningSectorsView, ScreeningView
from .settings_views import ApiConfigDetailView, ApiConfigListView
from .sync_views import SyncLogListView, SyncTriggerView
from .technical_views import StockTechnicalView

urlpatterns = [
    path("stocks/", views.StockListView.as_view(), name="stock-list"),
    path("stocks/recommendations/", RecommendationsView.as_view(), name="stock-recommendations"),
    path("stocks/screening/", ScreeningView.as_view(), name="stock-screening"),
    path("stocks/screening/sectors/", ScreeningSectorsView.as_view(), name="screening-sectors"),
    path("stocks/screening/presets/", ScreeningPresetListView.as_view(), name="screening-preset-list"),
    path("stocks/screening/presets/<int:pk>/", ScreeningPresetDetailView.as_view(), name="screening-preset-detail"),
    path("stocks/etf/", EtfListView.as_view(), name="etf-list"),
    path("stocks/reit/", ReitListView.as_view(), name="reit-list"),
    path("stocks/sync/", SyncTriggerView.as_view(), name="sync-trigger"),
    path("stocks/sync/logs/", SyncLogListView.as_view(), name="sync-log-list"),
    path("stocks/<str:code>/", views.StockDetailView.as_view(), name="stock-detail"),
    path("stocks/<str:code>/financials/", views.StockFinancialListView.as_view(), name="stock-financial-list"),
    path("stocks/<str:code>/financials/manual/", ManualFinancialListView.as_view(), name="stock-financial-manual-list"),
    path(
        "stocks/<str:code>/financials/manual/<int:fiscal_year>/",
        ManualFinancialDetailView.as_view(),
        name="stock-financial-manual-detail",
    ),
    path("stocks/<str:code>/financials/reset/", FinancialResetView.as_view(), name="stock-financial-reset"),
    path("stocks/<str:code>/margin/", StockMarginView.as_view(), name="stock-margin"),
    path("stocks/<str:code>/prices/", views.StockPriceListView.as_view(), name="stock-price-list"),
    path("stocks/<str:code>/technical/", StockTechnicalView.as_view(), name="stock-technical"),
    path("stocks/<str:code>/dividends/", views.StockDividendListView.as_view(), name="stock-dividend-list"),
    path("settings/api-configs/", ApiConfigListView.as_view(), name="api-config-list"),
    path("settings/api-configs/<str:provider>/", ApiConfigDetailView.as_view(), name="api-config-detail"),
]
