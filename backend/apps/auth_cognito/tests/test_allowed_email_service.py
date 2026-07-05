"""AllowedEmailService のテスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.allowed_email_service import (
    AllowedEmailService,
)
from apps.auth_cognito.infrastructure.models import UserAllowedEmail
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoUserAllowedEmailRepository,
)

pytestmark = pytest.mark.django_db


def _make_service() -> AllowedEmailService:
    return AllowedEmailService(allowed_repo=DjangoUserAllowedEmailRepository())


class TestAllowedEmailService:
    def test_add_allowed_email(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )

        info = _make_service().add(user_id=user.pk, email="alice+g@gmail.com", label="Google")

        assert info.id > 0
        assert info.email == "alice+g@gmail.com"
        assert info.label == "Google"
        assert UserAllowedEmail.objects.filter(email="alice+g@gmail.com").exists()

    def test_add_duplicate_email_raises(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="dup", email="dup@example.com"
        )
        UserAllowedEmail.objects.create(user=user, email="dup@example.com")

        with pytest.raises(ValueError, match="既に他で許可登録されています"):
            _make_service().add(user_id=user.pk, email="dup@example.com")

    def test_add_for_nonexistent_user_raises(self) -> None:
        with pytest.raises(ValueError, match="ユーザーが存在しません"):
            _make_service().add(user_id=9999, email="ghost@example.com")

    def test_remove_allowed_email(self) -> None:
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        allowed = UserAllowedEmail.objects.create(user=user, email="alice@example.com")

        _make_service().remove(allowed_id=allowed.pk, user_id=user.pk)

        assert not UserAllowedEmail.objects.filter(pk=allowed.pk).exists()

    def test_remove_for_wrong_user_raises(self) -> None:
        owner = get_user_model()._default_manager.create(  # noqa: SLF001
            username="owner", email="owner@example.com"
        )
        other = get_user_model()._default_manager.create(  # noqa: SLF001
            username="other", email="other@example.com"
        )
        allowed = UserAllowedEmail.objects.create(user=owner, email="owner@example.com")

        with pytest.raises(ValueError, match="属していません"):
            _make_service().remove(allowed_id=allowed.pk, user_id=other.pk)

        # 削除されていないこと
        assert UserAllowedEmail.objects.filter(pk=allowed.pk).exists()
