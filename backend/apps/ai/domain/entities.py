"""AI機能ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class AiConfigEntity:
    """ユーザーAI設定エンティティ"""

    user_id: int
    provider: str
    api_key: str
    model: str
    is_enabled: bool
    id: int | None = None
    updated_at: datetime | None = None


@dataclass
class AiAnalysisLogEntity:
    """AI分析ログエンティティ"""

    user_id: int
    stock_id: int | None
    question_type: str
    model_used: str
    custom_question: str = ""
    expert_role: str = "general"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    is_success: bool = True
    error_message: str = ""
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class AiDecisionEntity:
    """AI 投資判断エンティティ (buy/sell/hold/watch)"""

    user_id: int
    stock_id: int
    decision_type: str  # "buy" / "sell" / "hold" / "watch"
    rationale: str
    ai_model: str = ""
    confidence: Decimal | None = None  # 0.00〜1.00
    snapshot_indicators: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    decided_at: datetime | None = None
