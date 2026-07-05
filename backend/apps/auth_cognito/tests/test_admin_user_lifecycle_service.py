"""AdminUserLifecycleService のテスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.admin_user_lifecycle_service import (
    AdminUserLifecycleService,
)
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail

pytestmark = pytest.mark.django_db


class TestAdminUserLifecycleService:
    def test_disable_sets_is_active_false(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="u1", email="u1@example.com", is_active=True
        )
        AdminUserLifecycleService().disable(user.pk)
        user.refresh_from_db()
        assert user.is_active is False

    def test_enable_sets_is_active_true(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="u2", email="u2@example.com", is_active=False
        )
        AdminUserLifecycleService().enable(user.pk)
        user.refresh_from_db()
        assert user.is_active is True

    def test_disable_for_nonexistent_user_raises(self) -> None:
        with pytest.raises(ValueError, match="存在しません"):
            AdminUserLifecycleService().disable(99999)

    def test_delete_removes_user_and_cascades(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="u3", email="u3@example.com"
        )
        CognitoLink.objects.create(cognito_sub="sub-3", user=user, provider="cognito")
        UserAllowedEmail.objects.create(user=user, email="u3@example.com")

        AdminUserLifecycleService().delete(user.pk)

        assert not get_user_model()._default_manager.filter(pk=user.pk).exists()  # noqa: SLF001
        # CASCADE で関連も消える
        assert not CognitoLink.objects.filter(cognito_sub="sub-3").exists()
        assert not UserAllowedEmail.objects.filter(email="u3@example.com").exists()

    def test_delete_for_nonexistent_user_raises(self) -> None:
        with pytest.raises(ValueError, match="存在しません"):
            AdminUserLifecycleService().delete(99999)
