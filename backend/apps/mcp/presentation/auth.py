"""MCP API キー用 DRF Authentication クラス。

Authorization: Bearer fvc_mcp_xxxxx 形式のキーを受け取り、Django User を解決する。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

if TYPE_CHECKING:
    from rest_framework.request import Request

logger = logging.getLogger(__name__)

_BEARER_PREFIX = "Bearer "


class McpApiKeyAuthentication(BaseAuthentication):
    """`Authorization: Bearer fvc_mcp_xxxxx` ヘッダで認証する。"""

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[Any, str] | None:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header or not auth_header.startswith(_BEARER_PREFIX):
            return None  # 他の認証クラスにフォールバック（JWT 等）

        raw_key = auth_header[len(_BEARER_PREFIX) :].strip()
        if not raw_key.startswith("fvc_mcp_"):
            return None  # MCP キーではないので他の認証に委ねる

        # ローカルインポート（Django ready 後）
        from config import container

        usecase = container.authenticate_api_key_usecase()
        user = usecase.execute(raw_key)
        if user is None:
            raise AuthenticationFailed("Invalid or revoked MCP API key")

        if not user.is_active:
            raise AuthenticationFailed("User is disabled")

        return (user, raw_key)

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="mcp"'
