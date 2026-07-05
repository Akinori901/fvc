"""チャット機能ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class ChatSessionEntity:
    """チャットセッションエンティティ。

    1 ユーザーは複数のセッションを持てる。セッションは provider
    （gemini / openai / openai_admin）を保持し、途中で切り替わった場合も履歴を保全する。
    """

    user_id: int
    provider: str  # "gemini" / "openai" / "openai_admin"
    title: str = ""
    id: int | None = None
    started_at: datetime | None = None
    last_message_at: datetime | None = None


@dataclass
class ChatMessageEntity:
    """チャットメッセージエンティティ。

    Function Calling のツール呼び出しも 1 レコードずつ保存する:
    - role="user": ユーザー入力
    - role="assistant": LLM 応答（最終回答 or tool_calls 中間応答）
    - role="tool": ツール実行結果
    """

    session_id: int
    role: str  # "user" / "assistant" / "tool"
    content: str = ""
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_result: dict[str, Any] = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_used: str = ""
    provider: str = ""  # "gemini" / "openai" / "openai_admin"
    id: int | None = None
    created_at: datetime | None = None
