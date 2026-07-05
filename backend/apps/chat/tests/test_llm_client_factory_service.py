"""LlmClientFactoryService のテスト。"""

from __future__ import annotations

import pytest

from apps.ai.application.services.gemini_client_service import GeminiClientService
from apps.ai.application.services.openai_client_service import OpenAiClientService
from apps.chat.application.services.llm_client_factory_service import LlmClientFactoryService


class TestLlmClientFactoryService:
    def test_creates_gemini_client(self) -> None:
        factory = LlmClientFactoryService()
        client = factory.create(provider="gemini", api_key="dummy", model="gemini-2.5-flash")
        assert isinstance(client, GeminiClientService)

    def test_creates_openai_client(self) -> None:
        factory = LlmClientFactoryService()
        client = factory.create(provider="openai", api_key="dummy", model="gpt-4o-mini")
        assert isinstance(client, OpenAiClientService)

    def test_openai_admin_uses_openai_client(self) -> None:
        """管理者キー利用時も OpenAI クライアント。api_key は呼び出し側で管理者キーを渡す。"""
        factory = LlmClientFactoryService()
        client = factory.create(provider="openai_admin", api_key="admin-key", model="gpt-4o")
        assert isinstance(client, OpenAiClientService)

    def test_unknown_provider_raises(self) -> None:
        factory = LlmClientFactoryService()
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            factory.create(provider="anthropic", api_key="dummy", model="claude-3-5")
