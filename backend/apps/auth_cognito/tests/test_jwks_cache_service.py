"""JwksCacheService のテスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import httpx
import pytest

from apps.auth_cognito.application.services.jwks_cache_service import JwksCacheService
from apps.auth_cognito.domain.exceptions import CognitoJwksFetchError

if TYPE_CHECKING:
    from typing import Any

_JWKS_URL = "https://cognito-idp.ap-northeast-1.amazonaws.com/pool/.well-known/jwks.json"


def _jwks_response(keys: list[dict[str, Any]]) -> httpx.Response:
    request = httpx.Request("GET", _JWKS_URL)
    return httpx.Response(200, json={"keys": keys}, request=request)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    from django.core.cache import cache

    cache.clear()


class TestJwksCacheServiceFetch:
    def test_fetches_and_caches_jwks_on_first_call(self) -> None:
        service = JwksCacheService(jwks_url=_JWKS_URL)
        keys = [{"kid": "k1", "kty": "RSA"}, {"kid": "k2", "kty": "RSA"}]

        with patch("httpx.get", return_value=_jwks_response(keys)) as mocked:
            result = service.get_signing_key("k1")
            # 同じ kid を 2 回目に取ってもキャッシュからヒットして HTTP は呼ばれない
            service.get_signing_key("k2")

        assert result["kid"] == "k1"
        assert mocked.call_count == 1

    def test_refreshes_on_kid_miss(self) -> None:
        service = JwksCacheService(jwks_url=_JWKS_URL)
        first_keys = [{"kid": "old", "kty": "RSA"}]
        second_keys = [{"kid": "old", "kty": "RSA"}, {"kid": "new", "kty": "RSA"}]

        responses = [_jwks_response(first_keys), _jwks_response(second_keys)]
        with patch("httpx.get", side_effect=responses) as mocked:
            # 初回: old を取りに行く（キャッシュなし → HTTP）
            service.get_signing_key("old")
            # 2 回目: new はキャッシュにない → 再取得して取得できる
            result = service.get_signing_key("new")

        assert result["kid"] == "new"
        assert mocked.call_count == 2

    def test_raises_when_kid_not_in_refreshed_jwks(self) -> None:
        service = JwksCacheService(jwks_url=_JWKS_URL)
        keys = [{"kid": "k1", "kty": "RSA"}]

        with (
            patch("httpx.get", return_value=_jwks_response(keys)),
            pytest.raises(CognitoJwksFetchError, match="not found"),
        ):
            service.get_signing_key("unknown_kid")

    def test_raises_on_http_error(self) -> None:
        service = JwksCacheService(jwks_url=_JWKS_URL)

        def _raise(*args: Any, **kwargs: Any) -> httpx.Response:
            raise httpx.ConnectError("boom")

        with (
            patch("httpx.get", side_effect=_raise),
            pytest.raises(CognitoJwksFetchError, match="Failed to fetch JWKS"),
        ):
            service.get_signing_key("k1")

    def test_raises_on_malformed_response(self) -> None:
        service = JwksCacheService(jwks_url=_JWKS_URL)
        bad_response = httpx.Response(
            200,
            json={"unexpected": "shape"},
            request=httpx.Request("GET", _JWKS_URL),
        )

        with (
            patch("httpx.get", return_value=bad_response),
            pytest.raises(CognitoJwksFetchError, match="Invalid JWKS response"),
        ):
            service.get_signing_key("k1")

    def test_raises_when_url_is_empty(self) -> None:
        service = JwksCacheService(jwks_url="")
        with pytest.raises(CognitoJwksFetchError, match="not configured"):
            service.get_signing_key("k1")
