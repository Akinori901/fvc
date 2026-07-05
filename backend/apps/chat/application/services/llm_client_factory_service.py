"""LLM クライアントのファクトリ。

provider 文字列に応じて OpenAI / Gemini のクライアントを返す。
apps/chat のオーケストレーションが provider 非依存で動くための隠蔽層。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.ai.application.services.gemini_client_service import GeminiClientService
from apps.ai.application.services.openai_client_service import OpenAiClientService

if TYPE_CHECKING:
    from apps.chat.domain.llm_client import AbstractLlmClient


class LlmClientFactoryService:
    """provider に応じた LLM クライアントを生成する。

    provider:
      - "gemini": GeminiClientService
      - "openai": OpenAiClientService
      - "openai_admin": OpenAiClientService（管理者キー使用、SendChatMessageUseCase が
        管理者キーを api_key に渡す）
    """

    def create(self, provider: str, api_key: str, model: str) -> AbstractLlmClient:
        if provider == "gemini":
            return GeminiClientService(api_key=api_key, model=model)
        if provider in ("openai", "openai_admin"):
            return OpenAiClientService(api_key=api_key, model=model)
        raise ValueError(f"Unknown LLM provider: {provider}")
