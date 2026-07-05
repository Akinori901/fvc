"""MCP / 外部AI連携 ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


# キー形式
API_KEY_PREFIX_LITERAL = "fvc_mcp_"
API_KEY_PREFIX_LENGTH = 8  # DB に保存する識別用 prefix の長さ


@dataclass
class McpApiKeyEntity:
    """MCP API キーのエンティティ。"""

    user_id: int
    label: str
    key_prefix: str
    key_hash: str
    is_active: bool = True
    last_used_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
