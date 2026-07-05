from django.urls import path

from . import views

urlpatterns = [
    path("valuations/calculate/", views.ValuationCalculateView.as_view(), name="valuation-calculate"),
    path(
        "valuations/reverse-calculate/",
        views.ValuationReverseCalculateView.as_view(),
        name="valuation-reverse-calculate",
    ),
    path("valuations/", views.ValuationListView.as_view(), name="valuation-list"),
    path("valuations/<int:pk>/", views.ValuationDetailView.as_view(), name="valuation-detail"),
    path("stocks/<str:code>/valuations/", views.StockValuationListView.as_view(), name="stock-valuation-list"),
]
