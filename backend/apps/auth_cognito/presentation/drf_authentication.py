"""Cognito 発行 JWT を検証する DRF Authentication Class。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.auth_cognito.domain.exceptions import InvalidCognitoTokenError, UserNotAllowedError

if TYPE_CHECKING:
    from rest_framework.request import Request

logger = logging.getLogger(__name__)

_BEARER_PREFIX = "Bearer "
_MCP_KEY_PREFIX = "fvc_mcp_"


class CognitoJWTAuthentication(BaseAuthentication):
    """`Authorization: Bearer <cognito_jwt>` ヘッダを検証する。

    DRF の認証チェーンに乗せるため、「自分が責任を持たないトークン」は必ず
    `None` を返してフォールバックさせる:

    - `Bearer` 形式でない                          → None
    - 空 token                                     → None
    - MCP API キー (`fvc_mcp_*`)                   → None (`McpApiKeyAuthentication` へ)
    - JWT として decode できない                    → None (SimpleJWT 等へ)
    - `iss` claim が Cognito issuer と一致しない    → None (SimpleJWT 等へ)
    - 上記を通過した本物の Cognito JWT のみ verify  → 検証失敗時に AuthenticationFailed

    過去インシデント (2026-05-22) では検証失敗時に常に AuthenticationFailed を
    raise していたため、SimpleJWT 発行トークンが Cognito クラスで蹴られ、
    SimpleJWT 認証クラスへフォールバックされず全 API が 401 になった。
    本実装では「自分が責任を持つトークン」を `iss` で判定してから verify する。
    """

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[Any, str] | None:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header or not auth_header.startswith(_BEARER_PREFIX):
            return None

        token = auth_header[len(_BEARER_PREFIX) :].strip()
        if not token:
            return None

        # MCP API キーは別認証クラスに委ねる
        if token.startswith(_MCP_KEY_PREFIX):
            return None

        # Cognito JWT かどうかを iss claim で先に判定する。
        # 署名検証はせず payload を peek するだけなので、ここで信頼してはいけない。
        # 「Cognito JWT のフリをした攻撃」は後段の verify (署名検証) で必ず弾かれる。
        if not self._looks_like_cognito_token(token):
            return None

        from config import container

        verifier = container.cognito_jwt_verifier_service()
        provision = container.jit_provision_service()
        link_repo = container.cognito_link_repository()

        try:
            claims = verifier.verify(token)
        except InvalidCognitoTokenError as e:
            logger.info("Cognito JWT verification failed: %s", e)
            raise AuthenticationFailed("Invalid Cognito token") from e

        try:
            user = provision.provision(claims)
        except UserNotAllowedError as e:
            logger.info("Cognito JIT rejected: %s", e)
            raise AuthenticationFailed(str(e)) from e
        if not user.is_active:
            raise AuthenticationFailed("User is disabled")

        # last_signed_in_at の更新（best-effort、失敗しても認証は通す）
        try:
            link = link_repo.find_by_sub(claims.sub)
            if link is not None and link.id is not None:
                link_repo.touch_last_signed_in(link.id)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to update last_signed_in_at for sub=%s", claims.sub, exc_info=True)

        # request 側で参照したい場合があるので JWT 文字列を auth に積む
        return (user, token)

    @staticmethod
    def _looks_like_cognito_token(token: str) -> bool:
        """payload の iss claim で Cognito 発行トークンかを peek する (署名未検証)。

        - `COGNITO_JWT_ISSUER` 未設定環境では常に False (=フォールバック)
        - decode 不能 / iss なし / iss 不一致なら False
        - 一致したら True (この後で署名 + 全 claim 検証を行う)
        """
        expected_issuer = settings.COGNITO_JWT_ISSUER
        if not expected_issuer:
            return False
        try:
            unverified = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
            )
        except jwt.PyJWTError:
            return False
        return unverified.get("iss") == expected_issuer

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="cognito"'
