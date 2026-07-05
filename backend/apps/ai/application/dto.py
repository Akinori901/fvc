"""AI機能DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class AiConfigDTO:
    provider: str
    model: str
    is_enabled: bool
    has_api_key: bool
    updated_at: datetime | None = None


@dataclass
class StockContextDTO:
    """プロンプトに渡す銘柄コンテキスト"""

    code: str
    name: str
    sector: str
    latest_price: Decimal | None
    bps: Decimal | None
    eps: Decimal | None
    roe: Decimal | None
    revenue: int | None
    operating_income: int | None
    pbr: Decimal | None
    fair_value: Decimal | None
    discount_rate: Decimal | None


@dataclass
class AnalysisRequestDTO:
    user_id: int
    stock_code: str
    question_type: str
    custom_question: str = ""
    expert_role: str = "general"


@dataclass
class AnalysisResultDTO:
    analysis: str
    model: str
    generated_at: datetime
    prompt_tokens: int
    completion_tokens: int
