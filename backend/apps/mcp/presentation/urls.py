"""MCP / 外部AI連携 URL ルーティング。"""

from django.urls import path

from .views.api_key_views import McpApiKeyListIssueView, McpApiKeyRevokeView
from .views.openapi_view import McpOpenApiView
from .views.tool_views import McpToolInvokeView, McpToolListView

urlpatterns = [
    # API キー管理（既存 JWT 認証）
    path("v1/mcp/keys/", McpApiKeyListIssueView.as_view(), name="mcp-keys"),
    path("v1/mcp/keys/<int:key_id>/", McpApiKeyRevokeView.as_view(), name="mcp-keys-revoke"),
    # ツール実行（MCP API キー認証）
    path("v1/mcp/tools/", McpToolListView.as_view(), name="mcp-tools-list"),
    path("v1/mcp/tools/<str:tool_name>", McpToolInvokeView.as_view(), name="mcp-tools-invoke"),
    # OpenAPI 仕様（YAML）
    path("v1/mcp/openapi.yaml", McpOpenApiView.as_view(), name="mcp-openapi"),
]
