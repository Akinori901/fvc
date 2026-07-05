"""MCP / 外部AI連携 DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class IssuedApiKeyDTO:
    """発行直後の API キー（平文を含む）。

    平文 `plain_key` は発行レスポンス 1 回のみ呼び出し側に返される。
    """

    id: int
    label: str
    key_prefix: str
    plain_key: str
    created_at: datetime


@dataclass
class ApiKeySummaryDTO:
    """API キー一覧表示用 DTO。"""

    id: int
    label: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
