"""CognitoUserPoolAdminService のテスト。"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
    CognitoUserPoolAdminService,
)
from apps.auth_cognito.domain.entities import CognitoUserInfo
from apps.auth_cognito.domain.repositories import CognitoUserPoolRepository
from apps.auth_cognito.infrastructure.models import CognitoLink
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoCognitoLinkRepository,
)


class _FakeUserPoolRepo(CognitoUserPoolRepository):
    """テスト用 Fake (boto3 を完全に置き換える)。"""

    def __init__(self, users: list[CognitoUserInfo] | None = None) -> None:
        self.users = {u.username: u for u in (users or [])}
        self.disable_calls: list[str] = []
        self.enable_calls: list[str] = []
        self.delete_calls: list[str] = []

    def list_users(self) -> list[CognitoUserInfo]:
        return list(self.users.values())

    def get_user(self, username: str) -> CognitoUserInfo | None:
        return self.users.get(username)

    def disable_user(self, username: str) -> None:
        self.disable_calls.append(username)

    def enable_user(self, username: str) -> None:
        self.enable_calls.append(username)

    def delete_user(self, username: str) -> None:
        self.delete_calls.append(username)
        self.users.pop(username, None)

    def admin_create_user(self, email: str) -> None:  # pragma: no cover - 未使用
        raise NotImplementedError

    def resend_invite(self, email: str) -> None:  # pragma: no cover - 未使用
        raise NotImplementedError


@pytest.mark.django_db
class TestCognitoUserPoolAdminService:
    def test_disable_calls_userpool(self) -> None:
        fake = _FakeUserPoolRepo()
        service = CognitoUserPoolAdminService(userpool_repo=fake, link_repo=DjangoCognitoLinkRepository())

        service.disable("u-1")

        assert fake.disable_calls == ["u-1"]

    def test_enable_calls_userpool(self) -> None:
        fake = _FakeUserPoolRepo()
        service = CognitoUserPoolAdminService(userpool_repo=fake, link_repo=DjangoCognitoLinkRepository())

        service.enable("u-1")

        assert fake.enable_calls == ["u-1"]

    def test_delete_calls_userpool_and_removes_link(self) -> None:
        # 既存 link を作る
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        sub = "11111111-2222-3333-4444-555555555555"
        CognitoLink.objects.create(cognito_sub=sub, user=user, provider="google")

        now = datetime.now(tz=UTC)
        fake = _FakeUserPoolRepo(
            users=[
                CognitoUserInfo(
                    username="Google_xxx",
                    sub=sub,
                    email="alice@example.com",
                    status="EXTERNAL_PROVIDER",
                    enabled=True,
                    user_create_date=now,
                    user_last_modified_date=now,
                    identity_provider="Google",
                )
            ]
        )
        service = CognitoUserPoolAdminService(userpool_repo=fake, link_repo=DjangoCognitoLinkRepository())

        service.delete("Google_xxx")

        assert fake.delete_calls == ["Google_xxx"]
        assert not CognitoLink.objects.filter(cognito_sub=sub).exists()

    def test_delete_when_no_link_succeeds(self) -> None:
        """Cognito 側にしかいないユーザーを削除してもエラーにならない。"""
        now = datetime.now(tz=UTC)
        fake = _FakeUserPoolRepo(
            users=[
                CognitoUserInfo(
                    username="orphan",
                    sub="orphan-sub",
                    email="orphan@example.com",
                    status="CONFIRMED",
                    enabled=True,
                    user_create_date=now,
                    user_last_modified_date=now,
                    identity_provider="Cognito",
                )
            ]
        )
        service = CognitoUserPoolAdminService(userpool_repo=fake, link_repo=DjangoCognitoLinkRepository())

        # 例外なく削除完了
        service.delete("orphan")
        assert fake.delete_calls == ["orphan"]
