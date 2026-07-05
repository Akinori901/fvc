"""OpenAPI 3 仕様書 View。ChatGPT Custom GPT Actions などからの登録用。

YAML ファイルをそのまま raw レスポンスで返す（ChatGPT Custom GPT は YAML を直接読み込める）。
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from django.conf import settings
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

if TYPE_CHECKING:
    from rest_framework.request import Request


# 検索パス（先頭から順に試す）
# - Docker (dev): /openapi を read-only volume マウント
# - Lambda (prod): BASE_DIR/openapi/... に Dockerfile が同梱する
# - ホスト直接実行: backend/../openapi
_CANDIDATE_PATHS = [
    "/openapi/api/paths/mcp_tools.yaml",  # Docker volume (dev)
    "openapi/api/paths/mcp_tools.yaml",  # BASE_DIR 直下（Lambda 本番）
    "../openapi/api/paths/mcp_tools.yaml",  # backend BASE_DIR からの相対（ホスト直接）
]


class McpOpenApiView(APIView):
    """GET /api/v1/mcp/openapi.yaml — OpenAPI 3 仕様（YAML をそのまま返す）。"""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> HttpResponse:
        base = str(getattr(settings, "BASE_DIR", os.getcwd()))
        for candidate in _CANDIDATE_PATHS:
            path = os.path.normpath(candidate if os.path.isabs(candidate) else os.path.join(base, candidate))
            if os.path.exists(path):
                with open(path, "rb") as f:
                    content = f.read()
                return HttpResponse(content, content_type="application/yaml")
        return HttpResponse(
            "openapi/api/paths/mcp_tools.yaml が見つかりません",
            status=500,
            content_type="text/plain; charset=utf-8",
        )
