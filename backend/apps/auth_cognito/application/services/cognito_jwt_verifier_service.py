"""Cognito JWT (access token) の署名 + claim 検証サービス。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import jwt
from jwt.algorithms import RSAAlgorithm

from apps.auth_cognito.domain.entities import CognitoClaimsEntity
from apps.auth_cognito.domain.exceptions import (
    CognitoJwksFetchError,
    InvalidCognitoTokenError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from apps.auth_cognito.application.services.jwks_cache_service import JwksCacheService

logger = logging.getLogger(__name__)

_ACCEPTED_TOKEN_USES = frozenset({"access", "id"})


class CognitoJwtVerifierService:
    """Cognito 発行 JWT を検証して `CognitoClaimsEntity` に変換する。

    検証ステップ:
    1. ヘッダから `kid` / `alg` を取り出し、`alg=RS256` を要求
    2. JWKS から `kid` 対応の公開鍵を取得
    3. PyJWT で署名 + `exp` / `iss` 検証
    4. `token_use` / `client_id` (= aud / `client_id` claim) を独自検証
    """

    def __init__(
        self,
        jwks_cache: JwksCacheService,
        issuer: str,
        allowed_client_ids: Iterable[str],
    ) -> None:
        """
        Args:
            jwks_cache: JWKS 取得・キャッシュサービス
            issuer: 想定する iss claim (`https://cognito-idp.<region>.amazonaws.com/<pool-id>`)
            allowed_client_ids: 受け付ける client_id の集合 (web client / GPT client)
        """
        self._jwks = jwks_cache
        self._issuer = issuer
        self._allowed_client_ids = frozenset(allowed_client_ids)

    def verify(self, token: str) -> CognitoClaimsEntity:
        """JWT を検証して claim を返す。

        Raises:
            InvalidCognitoTokenError: 署名・形式・claim 検証のいずれかに失敗
        """
        if not self._issuer:
            raise InvalidCognitoTokenError("Cognito issuer is not configured")
        if not self._allowed_client_ids:
            raise InvalidCognitoTokenError("No allowed Cognito client_ids configured")

        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as e:
            raise InvalidCognitoTokenError(f"Malformed JWT header: {e}") from e

        kid = header.get("kid")
        alg = header.get("alg")
        if not kid:
            raise InvalidCognitoTokenError("JWT header missing 'kid'")
        if alg != "RS256":
            raise InvalidCognitoTokenError(f"Unsupported JWT algorithm: {alg}")

        try:
            jwk = self._jwks.get_signing_key(kid)
        except CognitoJwksFetchError as e:
            raise InvalidCognitoTokenError(f"JWKS lookup failed: {e}") from e

        public_key = RSAAlgorithm.from_jwk(jwk)

        try:
            # access token には aud がない（Cognito 仕様）ので audience は検証しない。
            # 代わりに後段で client_id / token_use を検証する。
            payload: dict[str, Any] = jwt.decode(
                token,
                key=public_key,  # type: ignore[arg-type]
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False, "require": ["exp", "iss", "sub"]},
            )
        except jwt.ExpiredSignatureError as e:
            raise InvalidCognitoTokenError("Token expired") from e
        except jwt.InvalidIssuerError as e:
            raise InvalidCognitoTokenError("Invalid issuer") from e
        except jwt.PyJWTError as e:
            raise InvalidCognitoTokenError(f"JWT verification failed: {e}") from e

        token_use = payload.get("token_use", "")
        if token_use not in _ACCEPTED_TOKEN_USES:
            raise InvalidCognitoTokenError(f"Unexpected token_use: {token_use}")

        # access token は `client_id`、id token は `aud` に client_id が入る
        client_id = payload.get("client_id") or payload.get("aud", "")
        if isinstance(client_id, list):
            # aud が list の場合は最初の要素を採用（id token の仕様）
            client_id = client_id[0] if client_id else ""
        if client_id not in self._allowed_client_ids:
            raise InvalidCognitoTokenError(f"client_id not allowed: {client_id}")

        return CognitoClaimsEntity(
            sub=payload["sub"],
            client_id=client_id,
            token_use=token_use,
            provider=self._extract_provider(payload),
            email=payload.get("email", ""),
            name=self._extract_name(payload),
            email_verified=bool(payload.get("email_verified", False)),
        )

    @staticmethod
    def _extract_provider(payload: dict[str, Any]) -> str:
        """`identities` claim から IdP を判定する。

        identities が無ければ Cognito ネイティブ (email/password) と判断する。
        """
        identities = payload.get("identities")
        if isinstance(identities, list) and identities:
            provider_name = identities[0].get("providerName", "")
            return provider_name.lower() if provider_name else "cognito"
        return "cognito"

    @staticmethod
    def _extract_name(payload: dict[str, Any]) -> str:
        """name / given_name / cognito:username の順で取得する。"""
        for key in ("name", "given_name", "cognito:username"):
            value = payload.get(key)
            if value:
                return str(value)
        return ""
