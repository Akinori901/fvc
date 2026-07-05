from django.urls import path

from . import simulation_views, views

urlpatterns = [
    # 既存
    path("watchlist/", views.WatchlistListView.as_view(), name="watchlist-list"),
    path("watchlist/<str:stock_code>/", views.WatchlistDetailView.as_view(), name="watchlist-detail"),
    # 家族ポートフォリオ
    path("family-members/", views.FamilyMemberListView.as_view(), name="family-member-list"),
    path("family-members/<int:pk>/", views.FamilyMemberDetailView.as_view(), name="family-member-detail"),
    path("portfolio-accounts/", views.PortfolioAccountListView.as_view(), name="portfolio-account-list"),
    path("portfolio-accounts/<int:pk>/", views.PortfolioAccountDetailView.as_view(), name="portfolio-account-detail"),
    path(
        "portfolio-accounts/<int:account_id>/snapshots/",
        views.AccountSnapshotListView.as_view(),
        name="account-snapshot-list",
    ),
    path(
        "portfolio-accounts/<int:account_id>/snapshots/<str:snapshot_date>/",
        views.AccountSnapshotDetailView.as_view(),
        name="account-snapshot-detail",
    ),
    path(
        "family-portfolio/dashboard/", views.FamilyPortfolioDashboardView.as_view(), name="family-portfolio-dashboard"
    ),
    path("family-portfolio/import-csv/", views.CsvImportView.as_view(), name="csv-import"),
    path("family-portfolio/history/", views.FamilyPortfolioHistoryView.as_view(), name="family-portfolio-history"),
    path(
        "family-portfolio/share-dashboard/",
        views.ShareDashboardView.as_view(),
        name="share-dashboard",
    ),
    path(
        "family-portfolio/simulation/",
        simulation_views.PortfolioSimulationView.as_view(),
        name="portfolio-simulation",
    ),
]
