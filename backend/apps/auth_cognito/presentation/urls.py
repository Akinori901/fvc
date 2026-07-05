"""Admin 管理 API ルーティング。"""

from __future__ import annotations

from django.urls import path

from apps.auth_cognito.presentation.views.admin_allowed_email_view import (
    AdminAllowedEmailCreateView,
    AdminAllowedEmailDestroyView,
)
from apps.auth_cognito.presentation.views.admin_cognito_link_view import (
    AdminCognitoLinkDestroyView,
)
from apps.auth_cognito.presentation.views.admin_cognito_user_view import (
    AdminCognitoUserDestroyView,
    AdminCognitoUserDisableView,
    AdminCognitoUserEnableView,
    AdminCognitoUserListView,
)
from apps.auth_cognito.presentation.views.admin_user_view import (
    AdminUserDestroyView,
    AdminUserDisableView,
    AdminUserEnableView,
    AdminUserListCreateView,
)

urlpatterns = [
    path("admin/users/", AdminUserListCreateView.as_view(), name="admin-users"),
    path(
        "admin/users/<int:user_id>/",
        AdminUserDestroyView.as_view(),
        name="admin-user-destroy",
    ),
    path(
        "admin/users/<int:user_id>/disable/",
        AdminUserDisableView.as_view(),
        name="admin-user-disable",
    ),
    path(
        "admin/users/<int:user_id>/enable/",
        AdminUserEnableView.as_view(),
        name="admin-user-enable",
    ),
    path(
        "admin/users/<int:user_id>/allowed-emails/",
        AdminAllowedEmailCreateView.as_view(),
        name="admin-allowed-email-create",
    ),
    path(
        "admin/users/<int:user_id>/allowed-emails/<int:allowed_id>/",
        AdminAllowedEmailDestroyView.as_view(),
        name="admin-allowed-email-destroy",
    ),
    path(
        "admin/users/<int:user_id>/cognito-links/<int:link_id>/",
        AdminCognitoLinkDestroyView.as_view(),
        name="admin-cognito-link-destroy",
    ),
    path(
        "admin/cognito-users/",
        AdminCognitoUserListView.as_view(),
        name="admin-cognito-users",
    ),
    path(
        "admin/cognito-users/<str:username>/",
        AdminCognitoUserDestroyView.as_view(),
        name="admin-cognito-user-destroy",
    ),
    path(
        "admin/cognito-users/<str:username>/disable/",
        AdminCognitoUserDisableView.as_view(),
        name="admin-cognito-user-disable",
    ),
    path(
        "admin/cognito-users/<str:username>/enable/",
        AdminCognitoUserEnableView.as_view(),
        name="admin-cognito-user-enable",
    ),
]
