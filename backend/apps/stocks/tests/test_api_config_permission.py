"""API設定ビューの権限テスト。"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.stocks.models import ApiConfig

_URL = "/api/settings/api-configs/edinet/"


@pytest.fixture
def _client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestApiConfigDetailPermission:
    def test_anonymous_cannot_update(self, _client: APIClient) -> None:
        res = _client.put(_URL, {"api_key": "leaked"}, format="json")
        assert res.status_code in (401, 403)

    def test_normal_user_cannot_update(self, _client: APIClient) -> None:
        # 一般ユーザーによるAPIキー書き換えを防ぐ
        user = get_user_model()._default_manager.create_user(  # noqa: SLF001
            username="normal", email="normal@example.com", password="pw"
        )
        _client.force_authenticate(user=user)

        res = _client.put(_URL, {"api_key": "leaked"}, format="json")

        assert res.status_code == 403
        assert not ApiConfig.objects.filter(provider="edinet").exists()

    def test_superuser_can_update(self, _client: APIClient) -> None:
        admin = get_user_model()._default_manager.create_superuser(  # noqa: SLF001
            username="admin", email="admin@example.com", password="pw"
        )
        _client.force_authenticate(user=admin)

        res = _client.put(_URL, {"api_key": "new-key", "is_enabled": True}, format="json")

        assert res.status_code == 200
        config = ApiConfig.objects.get(provider="edinet")
        assert config.api_key == "new-key"
        assert config.is_enabled is True

    def test_response_does_not_expose_api_key(self, _client: APIClient) -> None:
        admin = get_user_model()._default_manager.create_superuser(  # noqa: SLF001
            username="admin2", email="admin2@example.com", password="pw"
        )
        _client.force_authenticate(user=admin)

        res = _client.put(_URL, {"api_key": "secret-value"}, format="json")

        assert "api_key" not in res.json()
        assert "secret-value" not in str(res.json())
