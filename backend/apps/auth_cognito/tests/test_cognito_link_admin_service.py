"""CognitoLinkAdminService のテスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.cognito_link_admin_service import (
    CognitoLinkAdminService,
)
from apps.auth_cognito.infrastructure.models import CognitoLink
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoCognitoLinkRepository,
)

pytestmark = pytest.mark.django_db


def _make_service() -> CognitoLinkAdminService:
    return CognitoLinkAdminService(link_repo=DjangoCognitoLinkRepository())


class TestCognitoLinkAdminService:
    def test_delete_link(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        link = CognitoLink.objects.create(cognito_sub="alice-sub", user=user, provider="google")

        _make_service().delete(link_id=link.pk, user_id=user.pk)

        assert not CognitoLink.objects.filter(pk=link.pk).exists()

    def test_delete_for_wrong_user_raises(self) -> None:
        owner = get_user_model()._default_manager.create(  # noqa: SLF001
            username="owner", email="owner@example.com"
        )
        other = get_user_model()._default_manager.create(  # noqa: SLF001
            username="other", email="other@example.com"
        )
        link = CognitoLink.objects.create(cognito_sub="owner-sub", user=owner, provider="google")

        with pytest.raises(ValueError, match="属していません"):
            _make_service().delete(link_id=link.pk, user_id=other.pk)

        assert CognitoLink.objects.filter(pk=link.pk).exists()
