from django.contrib import admin
from django.urls import include, path

from apps.core.views import UserDetailsView

urlpatterns = [
    path("admin/", admin.site.urls),
    # 認証済みユーザー情報取得 (Cognito JWT 認証)
    # 旧 dj-rest-auth / SimpleJWT エンドポイント (/api/auth/login,
    # /api/auth/registration, /api/auth/token/refresh, /api/auth/password/change,
    # /api/auth/email/ 等) は Phase D で全削除済み。フロントエンド側も
    # Amplify SDK 経由で Cognito と直接通信する。
    path("api/auth/user/", UserDetailsView.as_view(), name="user_details"),
    path("api/", include("apps.stocks.presentation.urls")),
    path("api/", include("apps.valuations.presentation.urls")),
    path("api/", include("apps.portfolios.presentation.urls")),
    path("api/", include("apps.ai.presentation.urls")),
    path("api/", include("apps.fx.presentation.urls")),
    path("api/", include("apps.paper_trading.presentation.urls")),
    path("api/", include("apps.goals.presentation.urls")),
    path("api/", include("apps.news.presentation.urls")),
    path("api/", include("apps.mcp.presentation.urls")),
    path("api/chat/", include("apps.chat.presentation.urls")),
    path("api/", include("apps.auth_cognito.presentation.urls")),
]
