"""Cognito JWKS の取得・キャッシュサービス。"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from django.core.cache import cache

from apps.auth_cognito.domain.exceptions import CognitoJwksFetchError

logger = logging.getLogger(__name__)


class JwksCacheService:
    """Cognito の JWKS (JSON Web Key Set) を取得・キャッシュする。

    キャッシュ TTL は 1h。Lambda 環境では Django のローカルメモリキャッシュが
    コンテナ単位で有効なので、コールドスタート以外ではヒットする。
    署名検証時に kid が不一致なら強制再取得してキーローテーションに追従する。
    """

    _CACHE_KEY = "cognito_jwks_keys_v1"
    _TTL_SECONDS = 3600

    def __init__(self, jwks_url: str, *, http_timeout: float = 5.0) -> None:
        """
        Args:
            jwks_url: `https://cognito-idp.<region>.amazonaws.com/<pool-id>/.well-known/jwks.json`
            http_timeout: JWKS 取得時の HTTP タイムアウト（秒）
        """
        self._jwks_url = jwks_url
        self._timeout = http_timeout

    def get_signing_key(self, kid: str) -> dict[str, Any]:
        """指定 kid に対応する JWK を返す。

        キャッシュに無い、または kid が一致しない場合は JWKS を再取得する。

        Raises:
            CognitoJwksFetchError: JWKS の取得に失敗した、または kid に対応する鍵が無い
        """
        keys = cache.get(self._CACHE_KEY)
        if keys is None:
            keys = self._fetch()
            cache.set(self._CACHE_KEY, keys, self._TTL_SECONDS)

        match = self._find_kid(keys, kid)
        if match is not None:
            return match

        # kid 不一致 → ローテーション可能性ありなので強制再取得
        logger.info("Cognito JWKS kid not found in cache, refreshing: kid=%s", kid)
        keys = self._fetch()
        cache.set(self._CACHE_KEY, keys, self._TTL_SECONDS)
        match = self._find_kid(keys, kid)
        if match is None:
            raise CognitoJwksFetchError(f"Signing key not found for kid={kid}")
        return match

    def _fetch(self) -> list[dict[str, Any]]:
        if not self._jwks_url:
            raise CognitoJwksFetchError("JWKS URL is not configured")
        try:
            response = httpx.get(self._jwks_url, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise CognitoJwksFetchError(f"Failed to fetch JWKS: {e}") from e

        try:
            data = response.json()
            keys: list[dict[str, Any]] = data["keys"]
        except (ValueError, KeyError, TypeError) as e:
            raise CognitoJwksFetchError(f"Invalid JWKS response: {e}") from e
        return keys

    @staticmethod
    def _find_kid(keys: list[dict[str, Any]], kid: str) -> dict[str, Any] | None:
        return next((k for k in keys if k.get("kid") == kid), None)
