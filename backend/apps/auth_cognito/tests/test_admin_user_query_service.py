"""AdminUserQueryService のテスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.admin_user_query_service import (
    AdminUserQueryService,
)
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoCognitoLinkRepository,
    DjangoUserAllowedEmailRepository,
)

pytestmark = pytest.mark.django_db


def _make_service() -> AdminUserQueryService:
    return AdminUserQueryService(
        cognito_link_repo=DjangoCognitoLinkRepository(),
        allowed_email_repo=DjangoUserAllowedEmailRepository(),
    )


class TestAdminUserQueryService:
    def test_list_users_with_details_includes_links_and_allowed_emails(self) -> None:
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        # 1 user に 2 link + 2 allowed_emails を作る
        CognitoLink.objects.create(
            cognito_sub="alice-sub-1", user=user, provider="cognito", cognito_email="alice@example.com"
        )
        CognitoLink.objects.create(
            cognito_sub="alice-sub-2", user=user, provider="google", cognito_email="a.alice@gmail.com"
        )
        UserAllowedEmail.objects.create(user=user, email="alice@example.com")
        UserAllowedEmail.objects.create(user=user, email="a.alice@gmail.com", label="個人 Google")

        rows = _make_service().list_users_with_details()

        match = next(row for row in rows if row.id == user.pk)
        assert {link.cognito_sub for link in match.cognito_links} == {"alice-sub-1", "alice-sub-2"}
        assert {allowed.email for allowed in match.allowed_emails} == {
            "alice@example.com",
            "a.alice@gmail.com",
        }
        assert any(allowed.label == "個人 Google" for allowed in match.allowed_emails)

    def test_list_users_with_details_for_user_without_links_or_emails(self) -> None:
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="bob", email="bob@example.com"
        )

        rows = _make_service().list_users_with_details()

        match = next(row for row in rows if row.id == user.pk)
        assert match.cognito_links == []
        assert match.allowed_emails == []
