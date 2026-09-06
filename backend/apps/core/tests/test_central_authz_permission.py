"""中央認可と `IsSuperUser` の連携テスト。

いちばん守りたいのは **中央が落ちても既存の管理者が締め出されない**こと。
ここが壊れると、中央の障害時に誰も管理画面に入れなくなる。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rest_framework.request import Request

from apps.core.permissions import IsSuperUser
from apps.core.services import central_authz

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    """テスト間でキャッシュを持ち越さない。"""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


def _request(user: Any) -> Request:
    req = APIRequestFactory().get("/api/admin/whatever")
    req.user = user
    return req


# has_permission は view を使わないが、シグネチャ上 APIView が要る。
_VIEW = APIView()


@pytest.mark.django_db
class TestIsSuperUserWithCentral:
    def test_central_admin_is_allowed(self) -> None:
        """Django 側が一般ユーザーでも、中央が admin と言えば通る。

        これが「コンソールでロールを管理する」の実体。
        """
        user = User.objects.create_user(username="u1", email="a@example.com", password="x")
        with patch.object(central_authz, "fetch", return_value=central_authz.CentralAuthz(allowed=True, role="admin")):
            assert IsSuperUser().has_permission(_request(user), _VIEW) is True

    def test_central_member_falls_back_to_existing(self) -> None:
        user = User.objects.create_user(username="u2", email="b@example.com", password="x")
        with patch.object(central_authz, "fetch", return_value=central_authz.CentralAuthz(allowed=True, role="member")):
            assert IsSuperUser().has_permission(_request(user), _VIEW) is False

    def test_existing_superuser_survives_central_outage(self) -> None:
        """**最重要。** 中央の障害で管理画面から締め出されない。

        fetch は障害時に None を返す契約。拒否（allowed=False）と
        区別できないと、中央が落ちた瞬間に全員が閉め出される。
        """
        user = User.objects.create_superuser(username="u3", email="c@example.com", password="x")
        with patch.object(central_authz, "fetch", return_value=None):
            assert IsSuperUser().has_permission(_request(user), _VIEW) is True

    def test_existing_superuser_survives_central_denial(self) -> None:
        """移行中は「中央 OR 既存」。中央の登録漏れで締め出さない。"""
        user = User.objects.create_superuser(username="u4", email="d@example.com", password="x")
        with patch.object(
            central_authz, "fetch", return_value=central_authz.CentralAuthz(allowed=False, role="member")
        ):
            assert IsSuperUser().has_permission(_request(user), _VIEW) is True

    def test_anonymous_is_rejected(self) -> None:
        from django.contrib.auth.models import AnonymousUser

        assert IsSuperUser().has_permission(_request(AnonymousUser()), _VIEW) is False

    def test_plain_user_is_rejected(self) -> None:
        user = User.objects.create_user(username="u5", email="e@example.com", password="x")
        with patch.object(central_authz, "fetch", return_value=None):
            assert IsSuperUser().has_permission(_request(user), _VIEW) is False


class TestCentralAuthzFetch:
    def test_returns_none_when_url_unset(self, settings: Any) -> None:
        """移行前の状態。中央を使わない。"""
        settings.CENTRAL_AUTHZ_URL = ""
        assert central_authz.fetch("a@example.com") is None

    def test_returns_none_when_unreachable(self, settings: Any) -> None:
        """障害は拒否ではない。既存の判定に委ねる。"""
        settings.CENTRAL_AUTHZ_URL = "http://127.0.0.1:9"  # 誰も待ち受けていない
        settings.CENTRAL_AUTHZ_TIMEOUT = 0.2
        assert central_authz.fetch("a@example.com") is None

    def test_returns_none_for_empty_email(self, settings: Any) -> None:
        settings.CENTRAL_AUTHZ_URL = "https://example.com"
        assert central_authz.fetch("") is None
