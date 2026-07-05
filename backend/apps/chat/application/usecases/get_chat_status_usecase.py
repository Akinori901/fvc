"""BYOK 状態 + 当日使用量 を返す UseCase。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.ai.domain.repositories import AiConfigRepository
    from apps.chat.application.services.daily_limit_service import DailyLimitService


@dataclass
class ChatStatusDTO:
    has_config: bool
    is_enabled: bool
    provider: str
    model: str
    daily_used: int
    daily_limit: int
    daily_remaining: int


class GetChatStatusUseCase:
    """フロントエンドのウィジェット表示用に、BYOK 状態と本日の使用量を返す。"""

    def __init__(
        self,
        ai_config_repo: AiConfigRepository,
        daily_limit_service: DailyLimitService,
    ) -> None:
        self._ai_config_repo = ai_config_repo
        self._daily_limit_service = daily_limit_service

    def execute(self, user_id: int) -> ChatStatusDTO:
        config = self._ai_config_repo.find_by_user_id(user_id)
        has_config = config is not None
        is_enabled = bool(config and config.is_enabled and config.api_key and config.provider in ("gemini", "openai"))
        provider = config.provider if config else ""
        model = config.model if config else ""

        remaining = self._daily_limit_service.remaining(user_id=user_id)
        limit = self._daily_limit_service.limit
        used = max(0, limit - remaining)

        return ChatStatusDTO(
            has_config=has_config,
            is_enabled=is_enabled,
            provider=provider,
            model=model,
            daily_used=used,
            daily_limit=limit,
            daily_remaining=remaining,
        )
