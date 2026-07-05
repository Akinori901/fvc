"""AdminUserCreateService のテスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.admin_user_create_service import (
    AdminUserCreateService,
)

pytestmark = pytest.mark.django_db


class TestAdminUserCreateService:
    def test_create_user_success(self) -> None:
        service = AdminUserCreateService()

        row = service.create_user(email="new@example.com")

        user_model = get_user_model()
        user = user_model._default_manager.get(pk=row.id)  # noqa: SLF001
        assert user.email == "new@example.com"
        assert user.username == "new@example.com"
        assert user.has_usable_password() is False
        assert row.cognito_links == []
        assert row.allowed_emails == []

    def test_create_user_duplicate_email_raises(self) -> None:
        user_model = get_user_model()
        user_model._default_manager.create(  # noqa: SLF001
            username="dup_user", email="dup@example.com"
        )
        service = AdminUserCreateService()

        with pytest.raises(ValueError, match="既に登録されています"):
            service.create_user(email="dup@example.com")
