"""MCP / 外部AI連携 ドメイン例外。"""


class McpAuthError(Exception):
    """API キー認証エラー。"""


class McpApiKeyNotFoundError(Exception):
    """指定された API キーが存在しない。"""


class McpToolNotFoundError(Exception):
    """指定された MCP ツール名が存在しない。"""
