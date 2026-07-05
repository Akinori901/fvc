"""`UserDetailsView` の統合テスト。

Phase D で dj-rest-auth を撤去した代わりに自前実装した `/api/auth/user/`
が正しいレスポンスを返し、未認証アクセスを拒否することを確認する。
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def authenticated_client(db) -> tuple[APIClient, object]:  # type: ignore[no-untyped-def]
    user = get_user_model().objects.create_user(
        username="taro",
        email="taro@example.com",
        password="dummy-password",
        first_name="太郎",
        last_name="山田",
        is_superuser=False,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
class TestUserDetailsView:
    def test_returns_user_payload_for_authenticated_user(
        self,
        authenticated_client: tuple[APIClient, object],
    ) -> None:
        client, user = authenticated_client

        response = client.get("/api/auth/user/")

        assert response.status_code == 200
        data = response.json()
        assert data["pk"] == user.pk  # type: ignore[attr-defined]
        assert data["username"] == "taro"
        assert data["email"] == "taro@example.com"
        assert data["first_name"] == "太郎"
        assert data["last_name"] == "山田"
        assert data["is_superuser"] is False

    def test_returns_is_superuser_true_for_admin(self, db) -> None:  # type: ignore[no-untyped-def]
        user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="dummy-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/auth/user/")

        assert response.status_code == 200
        assert response.json()["is_superuser"] is True

    def test_rejects_unauthenticated_request(self, db) -> None:  # type: ignore[no-untyped-def]
        client = APIClient()

        response = client.get("/api/auth/user/")

        assert response.status_code == 401
