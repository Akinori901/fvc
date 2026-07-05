"""CognitoJwtVerifierService のテスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from apps.auth_cognito.application.services.cognito_jwt_verifier_service import (
    CognitoJwtVerifierService,
)
from apps.auth_cognito.application.services.jwks_cache_service import JwksCacheService
from apps.auth_cognito.domain.exceptions import (
    CognitoJwksFetchError,
    InvalidCognitoTokenError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .conftest import SigningKeyPair


_ISSUER = "https://cognito-idp.ap-northeast-1.amazonaws.com/pool"
_WEB_CLIENT = "web-client-id"
_GPT_CLIENT = "gpt-client-id"


def _make_verifier(signing_key: SigningKeyPair) -> CognitoJwtVerifierService:
    jwks_cache = MagicMock(spec=JwksCacheService)
    jwks_cache.get_signing_key.return_value = signing_key.jwk_public
    return CognitoJwtVerifierService(
        jwks_cache=jwks_cache,
        issuer=_ISSUER,
        allowed_client_ids=(_WEB_CLIENT, _GPT_CLIENT),
    )


class TestCognitoJwtVerifierVerify:
    def test_verifies_valid_access_token(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer=_ISSUER, client_id=_WEB_CLIENT)
        verifier = _make_verifier(signing_key)

        claims = verifier.verify(token)

        assert claims.sub == "user-sub-1"
        assert claims.client_id == _WEB_CLIENT
        assert claims.token_use == "access"
        assert claims.email == "user@example.com"
        assert claims.email_verified is True
        assert claims.provider == "cognito"  # identities なし → cognito

    def test_extracts_provider_from_identities(
        self, issue_token: Callable[..., str], signing_key: SigningKeyPair
    ) -> None:
        token = issue_token(
            issuer=_ISSUER,
            client_id=_WEB_CLIENT,
            provider_identities=[{"providerName": "Google", "providerType": "Google"}],
        )
        verifier = _make_verifier(signing_key)
        claims = verifier.verify(token)

        assert claims.provider == "google"

    def test_accepts_gpt_client(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer=_ISSUER, client_id=_GPT_CLIENT)
        verifier = _make_verifier(signing_key)
        claims = verifier.verify(token)

        assert claims.client_id == _GPT_CLIENT

    def test_rejects_expired_token(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer=_ISSUER, client_id=_WEB_CLIENT, expires_in=-60)
        verifier = _make_verifier(signing_key)

        with pytest.raises(InvalidCognitoTokenError, match="expired"):
            verifier.verify(token)

    def test_rejects_wrong_issuer(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer="https://evil.example.com/pool", client_id=_WEB_CLIENT)
        verifier = _make_verifier(signing_key)

        with pytest.raises(InvalidCognitoTokenError, match="issuer"):
            verifier.verify(token)

    def test_rejects_unknown_client_id(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer=_ISSUER, client_id="unknown-client")
        verifier = _make_verifier(signing_key)

        with pytest.raises(InvalidCognitoTokenError, match="client_id"):
            verifier.verify(token)

    def test_rejects_invalid_token_use(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        token = issue_token(issuer=_ISSUER, client_id=_WEB_CLIENT, token_use="refresh")
        verifier = _make_verifier(signing_key)

        with pytest.raises(InvalidCognitoTokenError, match="token_use"):
            verifier.verify(token)

    def test_rejects_non_rs256_algorithm(self, signing_key: SigningKeyPair) -> None:
        # HS256 で署名された token はヘッダの alg 値だけで早期拒否されることを確認する
        import jwt

        token = jwt.encode({"sub": "x"}, "secret", algorithm="HS256", headers={"kid": "test-kid"})
        verifier = _make_verifier(signing_key)

        with pytest.raises(InvalidCognitoTokenError, match="algorithm"):
            verifier.verify(token)

    def test_rejects_when_jwks_lookup_fails(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        jwks_cache = MagicMock(spec=JwksCacheService)
        jwks_cache.get_signing_key.side_effect = CognitoJwksFetchError("boom")
        verifier = CognitoJwtVerifierService(
            jwks_cache=jwks_cache,
            issuer=_ISSUER,
            allowed_client_ids=(_WEB_CLIENT,),
        )
        token = issue_token(issuer=_ISSUER, client_id=_WEB_CLIENT)

        with pytest.raises(InvalidCognitoTokenError, match="JWKS lookup failed"):
            verifier.verify(token)

    def test_rejects_when_issuer_not_configured(
        self, issue_token: Callable[..., str], signing_key: SigningKeyPair
    ) -> None:
        jwks_cache = MagicMock(spec=JwksCacheService)
        jwks_cache.get_signing_key.return_value = signing_key.jwk_public
        verifier = CognitoJwtVerifierService(
            jwks_cache=jwks_cache,
            issuer="",
            allowed_client_ids=(_WEB_CLIENT,),
        )
        token = issue_token(issuer=_ISSUER, client_id=_WEB_CLIENT)

        with pytest.raises(InvalidCognitoTokenError, match="issuer is not configured"):
            verifier.verify(token)


class TestCognitoJwtVerifierIdToken:
    def test_accepts_id_token_with_aud(self, issue_token: Callable[..., str], signing_key: SigningKeyPair) -> None:
        # id token は aud に client_id が入る（client_id claim なし）
        token = issue_token(
            issuer=_ISSUER,
            client_id="ignored",  # access token 経路では client_id を見るので、id token テストでは aud を使う
            token_use="id",
            extra={"aud": _WEB_CLIENT, "client_id": None},
        )
        verifier = _make_verifier(signing_key)
        # claim_id を None で上書きしているので、aud にフォールバック
        # （実装では client_id (None) or aud で判定するため通る）
        claims = verifier.verify(token)
        assert claims.token_use == "id"
        assert claims.client_id == _WEB_CLIENT
