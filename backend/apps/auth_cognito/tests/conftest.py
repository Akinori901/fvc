"""auth_cognito テスト用 fixture。

RSA 鍵ペアを 1 回だけ生成し、テスト全体で共有する（鍵生成は重いため）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class _SigningKeyPair:
    private_pem: bytes
    jwk_public: dict[str, Any]
    kid: str

    def issue(
        self,
        *,
        sub: str = "user-sub-1",
        issuer: str,
        client_id: str = "web-client-id",
        token_use: str = "access",
        email: str = "user@example.com",
        email_verified: bool = True,
        name: str = "Test User",
        provider_identities: list[dict[str, Any]] | None = None,
        expires_in: int = 3600,
        extra: dict[str, Any] | None = None,
        algorithm: str = "RS256",
        kid: str | None = None,
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": sub,
            "iss": issuer,
            "client_id": client_id,
            "token_use": token_use,
            "email": email,
            "email_verified": email_verified,
            "name": name,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        if provider_identities is not None:
            payload["identities"] = provider_identities
        if extra:
            payload.update(extra)

        return jwt.encode(
            payload,
            self.private_pem,
            algorithm=algorithm,
            headers={"kid": kid or self.kid},
        )


@pytest.fixture(scope="session")
def signing_key() -> _SigningKeyPair:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_key = private_key.public_key()
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk.update({"kid": "test-kid", "use": "sig", "alg": "RS256"})
    return _SigningKeyPair(private_pem=private_pem, jwk_public=jwk, kid="test-kid")


SigningKeyPair = _SigningKeyPair  # public alias


@pytest.fixture
def issue_token(signing_key: _SigningKeyPair) -> Callable[..., str]:
    """テスト内で claims を変えながらトークンを発行するヘルパ。"""

    def _issue(**kwargs: Any) -> str:
        return signing_key.issue(**kwargs)

    return _issue
