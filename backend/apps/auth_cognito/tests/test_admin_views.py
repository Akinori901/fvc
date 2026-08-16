"""Admin 管理 API のテスト (`/api/admin/...`)。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.auth_cognito.domain.entities import CognitoUserInfo
from apps.auth_cognito.domain.exceptions import CognitoUserAlreadyExistsError
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail

if TYPE_CHECKING:
    from django.contrib.auth.models import User


@pytest.fixture
def superuser_client(db) -> tuple[APIClient, User]:  # type: ignore[no-untyped-def]
    user = get_user_model().objects.create_superuser(username="admin", email="admin@example.com", password="dummy")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def regular_client(db) -> tuple[APIClient, User]:  # type: ignore[no-untyped-def]
    user = get_user_model().objects.create_user(username="guest", email="guest@example.com", password="dummy")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
class TestAdminUserListCreateView:
    def test_admin_users_list_requires_superuser(self, regular_client: tuple[APIClient, User]) -> None:
        client, _ = regular_client

        response = client.get("/api/admin/users/")

        assert response.status_code == 403

    def test_admin_users_list_returns_users_for_superuser(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _admin = superuser_client
        user_model = get_user_model()
        guest = user_model._default_manager.create(  # noqa: SLF001
            username="guest", email="guest@example.com"
        )
        CognitoLink.objects.create(
            cognito_sub="guest-sub",
            user=guest,
            provider="google",
            cognito_email="guest@example.com",
        )
        UserAllowedEmail.objects.create(user=guest, email="guest@example.com")

        response = client.get("/api/admin/users/")

        assert response.status_code == 200
        users = response.json()["users"]
        by_email = {u["email"]: u for u in users}
        assert by_email["admin@example.com"]["is_superuser"] is True
        assert by_email["admin@example.com"]["cognito_links"] == []
        assert by_email["admin@example.com"]["allowed_emails"] == []
        guest_row = by_email["guest@example.com"]
        assert len(guest_row["cognito_links"]) == 1
        assert guest_row["cognito_links"][0]["provider"] == "google"
        assert len(guest_row["allowed_emails"]) == 1
        assert guest_row["allowed_emails"][0]["email"] == "guest@example.com"

    def test_admin_users_create_success(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        fake = _FakeUserPoolRepo(users=[])

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post(
                "/api/admin/users/",
                data={"email": "new@example.com"},
                format="json",
            )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "new@example.com"
        # 作成時に allowed_emails にも 1 行 (auth_user.email と同じ) が登録される
        assert len(body["allowed_emails"]) == 1
        assert body["allowed_emails"][0]["email"] == "new@example.com"
        # Cognito 招待メールが送られたフラグ
        assert body["invite_email_sent"] is True

        assert UserAllowedEmail.objects.filter(email="new@example.com").exists()
        # Cognito admin_create_user が email で 1 回呼ばれている
        assert fake.invite_calls == ["new@example.com"]

    def test_admin_users_create_duplicate_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user_model = get_user_model()
        user_model._default_manager.create(  # noqa: SLF001
            username="dup_user", email="dup@example.com"
        )
        fake = _FakeUserPoolRepo(users=[])

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post(
                "/api/admin/users/",
                data={"email": "dup@example.com"},
                format="json",
            )

        assert response.status_code == 400
        assert "既に登録されています" in response.json()["detail"]
        # DB 失敗時は Cognito は呼ばれない
        assert fake.invite_calls == []

    def test_admin_users_create_when_cognito_fails_returns_warning_flag(
        self, superuser_client: tuple[APIClient, User]
    ) -> None:
        """Cognito 呼び出しが落ちても auth_user/allowed_email は残り、フラグだけ False で返る。"""
        client, _ = superuser_client
        fake = _FakeUserPoolRepo(
            users=[],
            invite_raises=RuntimeError("boto3 ClientError"),
        )

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post(
                "/api/admin/users/",
                data={"email": "cognito-down@example.com"},
                format="json",
            )

        assert response.status_code == 201
        body = response.json()
        assert body["invite_email_sent"] is False
        # DB はロールバックしない
        assert get_user_model()._default_manager.filter(email="cognito-down@example.com").exists()  # noqa: SLF001
        assert UserAllowedEmail.objects.filter(email="cognito-down@example.com").exists()
        assert fake.invite_calls == ["cognito-down@example.com"]

    def test_admin_users_create_when_cognito_user_already_exists(
        self, superuser_client: tuple[APIClient, User]
    ) -> None:
        """Cognito 側に既存ユーザーがある場合は 201 + invite_email_sent=False。"""
        client, _ = superuser_client
        fake = _FakeUserPoolRepo(
            users=[],
            invite_raises=CognitoUserAlreadyExistsError("existing@example.com"),
        )

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post(
                "/api/admin/users/",
                data={"email": "existing@example.com"},
                format="json",
            )

        assert response.status_code == 201
        body = response.json()
        assert body["invite_email_sent"] is False
        assert get_user_model()._default_manager.filter(email="existing@example.com").exists()  # noqa: SLF001


@pytest.mark.django_db
class TestAdminAllowedEmailViews:
    def test_add_allowed_email(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )

        response = client.post(
            f"/api/admin/users/{user.pk}/allowed-emails/",
            data={"email": "alice+g@gmail.com", "label": "Google"},
            format="json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "alice+g@gmail.com"
        assert body["label"] == "Google"
        assert UserAllowedEmail.objects.filter(user=user, email="alice+g@gmail.com").exists()

    def test_add_allowed_email_requires_superuser(self, regular_client: tuple[APIClient, User]) -> None:
        client, _ = regular_client

        response = client.post(
            "/api/admin/users/1/allowed-emails/",
            data={"email": "x@example.com"},
            format="json",
        )

        assert response.status_code == 403

    def test_add_allowed_email_duplicate_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        UserAllowedEmail.objects.create(user=user, email="dup@example.com")

        response = client.post(
            f"/api/admin/users/{user.pk}/allowed-emails/",
            data={"email": "dup@example.com"},
            format="json",
        )

        assert response.status_code == 400

    def test_remove_allowed_email(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        allowed = UserAllowedEmail.objects.create(user=user, email="alice@example.com")

        response = client.delete(f"/api/admin/users/{user.pk}/allowed-emails/{allowed.pk}/")

        assert response.status_code == 204
        assert not UserAllowedEmail.objects.filter(pk=allowed.pk).exists()

    def test_remove_allowed_email_for_wrong_user_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        owner = get_user_model()._default_manager.create(  # noqa: SLF001
            username="owner", email="owner@example.com"
        )
        other = get_user_model()._default_manager.create(  # noqa: SLF001
            username="other", email="other@example.com"
        )
        allowed = UserAllowedEmail.objects.create(user=owner, email="owner@example.com")

        response = client.delete(f"/api/admin/users/{other.pk}/allowed-emails/{allowed.pk}/")

        assert response.status_code == 400


@pytest.mark.django_db
class TestAdminCognitoLinkDestroyView:
    def test_delete_link(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        link = CognitoLink.objects.create(cognito_sub="alice-sub", user=user, provider="google")

        response = client.delete(f"/api/admin/users/{user.pk}/cognito-links/{link.pk}/")

        assert response.status_code == 204
        assert not CognitoLink.objects.filter(pk=link.pk).exists()

    def test_delete_link_for_wrong_user_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        owner = get_user_model()._default_manager.create(  # noqa: SLF001
            username="owner", email="owner@example.com"
        )
        other = get_user_model()._default_manager.create(  # noqa: SLF001
            username="other", email="other@example.com"
        )
        link = CognitoLink.objects.create(cognito_sub="owner-sub", user=owner, provider="google")

        response = client.delete(f"/api/admin/users/{other.pk}/cognito-links/{link.pk}/")

        assert response.status_code == 400


class _FakeUserPoolRepo:
    """テスト用 Fake。CognitoUserPoolRepository ABC 互換だが明示継承はしない。"""

    def __init__(
        self,
        users: list[CognitoUserInfo],
        *,
        invite_raises: Exception | None = None,
    ) -> None:
        self._users = {u.username: u for u in users}
        self.disable_calls: list[str] = []
        self.enable_calls: list[str] = []
        self.delete_calls: list[str] = []
        self.invite_calls: list[str] = []
        self._invite_raises = invite_raises

    def list_users(self) -> list[CognitoUserInfo]:
        return list(self._users.values())

    def get_user(self, username: str) -> CognitoUserInfo | None:
        return self._users.get(username)

    def disable_user(self, username: str) -> None:
        self.disable_calls.append(username)

    def enable_user(self, username: str) -> None:
        self.enable_calls.append(username)

    def delete_user(self, username: str) -> None:
        self.delete_calls.append(username)
        self._users.pop(username, None)

    def admin_create_user(self, email: str) -> None:
        self.invite_calls.append(email)
        if self._invite_raises is not None:
            raise self._invite_raises

    def resend_invite(self, email: str) -> None:
        self.invite_calls.append(email)


@pytest.mark.django_db
class TestAdminCognitoUserListView:
    def test_returns_with_mock_boto3(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client

        now = datetime.now(tz=UTC)
        fake_users = [
            CognitoUserInfo(
                username="alice-sub",
                sub="alice-sub",
                email="alice@example.com",
                status="EXTERNAL_PROVIDER",
                enabled=True,
                user_create_date=now,
                user_last_modified_date=now,
                identity_provider="Google",
            ),
        ]

        with patch(
            "config.container.cognito_userpool_repository",
            return_value=_FakeUserPoolRepo(fake_users),
        ):
            response = client.get("/api/admin/cognito-users/")

        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == 1
        assert users[0]["username"] == "alice-sub"
        assert users[0]["identity_provider"] == "Google"
        assert users[0]["linked_user_id"] is None


@pytest.mark.django_db
class TestAdminUserLifecycleViews:
    def test_disable_requires_superuser(self, regular_client: tuple[APIClient, User]) -> None:
        client, _ = regular_client
        response = client.post("/api/admin/users/1/disable/")
        assert response.status_code == 403

    def test_disable_success(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="target", email="target@example.com", is_active=True
        )

        response = client.post(f"/api/admin/users/{user.pk}/disable/")

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is False

    def test_disable_self_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, admin = superuser_client
        response = client.post(f"/api/admin/users/{admin.pk}/disable/")
        assert response.status_code == 400

    def test_enable_success(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="t2", email="t2@example.com", is_active=False
        )

        response = client.post(f"/api/admin/users/{user.pk}/enable/")

        assert response.status_code == 204
        user.refresh_from_db()
        assert user.is_active is True

    def test_delete_self_returns_400(self, superuser_client: tuple[APIClient, User]) -> None:
        client, admin = superuser_client
        response = client.delete(f"/api/admin/users/{admin.pk}/")
        assert response.status_code == 400
        # admin はまだ存在する
        assert get_user_model()._default_manager.filter(pk=admin.pk).exists()  # noqa: SLF001

    def test_delete_other_user_cascades(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="delete-me", email="dm@example.com"
        )
        CognitoLink.objects.create(cognito_sub="dm-sub", user=user, provider="cognito")

        response = client.delete(f"/api/admin/users/{user.pk}/")

        assert response.status_code == 204
        assert not get_user_model()._default_manager.filter(pk=user.pk).exists()  # noqa: SLF001
        assert not CognitoLink.objects.filter(cognito_sub="dm-sub").exists()


@pytest.mark.django_db
class TestAdminCognitoUserLifecycleViews:
    def _fake_with_user(self) -> _FakeUserPoolRepo:
        now = datetime.now(tz=UTC)
        return _FakeUserPoolRepo(
            users=[
                CognitoUserInfo(
                    username="Google_xxx",
                    sub="11111111-2222-3333-4444-555555555555",
                    email="alice@example.com",
                    status="EXTERNAL_PROVIDER",
                    enabled=True,
                    user_create_date=now,
                    user_last_modified_date=now,
                    identity_provider="Google",
                )
            ]
        )

    def test_cognito_disable_calls_userpool(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        fake = self._fake_with_user()

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post("/api/admin/cognito-users/Google_xxx/disable/")

        assert response.status_code == 204
        assert fake.disable_calls == ["Google_xxx"]

    def test_cognito_enable_calls_userpool(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        fake = self._fake_with_user()

        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.post("/api/admin/cognito-users/Google_xxx/enable/")

        assert response.status_code == 204
        assert fake.enable_calls == ["Google_xxx"]

    def test_cognito_delete_removes_link(self, superuser_client: tuple[APIClient, User]) -> None:
        client, _ = superuser_client
        # Cognito 側に存在する sub と一致する link を backend に作っておく
        user = get_user_model()._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        sub = "11111111-2222-3333-4444-555555555555"
        CognitoLink.objects.create(cognito_sub=sub, user=user, provider="google")

        fake = self._fake_with_user()
        with patch("config.container.cognito_userpool_repository", return_value=fake):
            response = client.delete("/api/admin/cognito-users/Google_xxx/")

        assert response.status_code == 204
        assert fake.delete_calls == ["Google_xxx"]
        assert not CognitoLink.objects.filter(cognito_sub=sub).exists()
