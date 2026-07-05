"""MCP ツール REST View。

GET /api/v1/mcp/tools/{tool_name}?<params>

認証は settings の DEFAULT_AUTHENTICATION_CLASSES を継承する:
- Cognito JWT (ChatGPT Custom GPT の OAuth 接続など)
- MCP API キー `Authorization: Bearer fvc_mcp_xxxxx` (Claude Desktop など)

REST は MCP の Streamable HTTP に対応していない ChatGPT Custom GPT Actions
等で使う。MCP プロトコルを直接話せるクライアントは `/mcp/*` 経路 (Streamable
HTTP) を使う。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

from ...application.services.tool_invocation_service import ALL_TOOLS
from ...domain.exceptions import McpToolNotFoundError

if TYPE_CHECKING:
    from rest_framework.request import Request


class McpToolListView(APIView):
    """GET /api/v1/mcp/tools/ — 利用可能なツール一覧。

    認証は settings.DEFAULT_AUTHENTICATION_CLASSES を継承
    (Cognito JWT または MCP API キー)。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({"tools": list(ALL_TOOLS)})


class McpToolInvokeView(APIView):
    """GET /api/v1/mcp/tools/{tool_name}?... — ツール実行。

    認証は settings.DEFAULT_AUTHENTICATION_CLASSES を継承
    (Cognito JWT または MCP API キー)。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, tool_name: str) -> Response:
        # クエリパラメータを dict にまとめる（DRF の QueryDict は str を返す）
        params: dict[str, Any] = {}
        for key, value in request.query_params.items():
            params[key] = value

        service = container.tool_invocation_service()
        assert isinstance(request.user.id, int)
        try:
            result = service.invoke(tool_name=tool_name, params=params, user_id=request.user.id)
        except McpToolNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError as exc:
            return Response(
                {"detail": f"必須パラメータが不足しています: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(result)
