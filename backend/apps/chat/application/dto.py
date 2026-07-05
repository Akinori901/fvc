"""チャット機能の DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SendMessageRequestDTO:
    """チャットメッセージ送信リクエスト。"""

    user_id: int  # ログイン必須
    user_message: str
    session_id: int | None = None  # None なら新規セッション作成
    use_admin_key: bool = False  # 管理者ロールのみ有効


@dataclass
class ToolCallSummaryDTO:
    """フロントエンド表示用のツール呼び出し概要。"""

    tool_name: str
    arguments: dict[str, Any]
    succeeded: bool


@dataclass
class SendMessageResponseDTO:
    """チャットメッセージ送信レスポンス。"""

    session_id: int
    assistant_message: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    iterations: int
    truncated: bool
    tool_calls_summary: list[ToolCallSummaryDTO]
