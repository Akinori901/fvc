"""AI設定取得ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.ai.application.dto import AiConfigDTO

if TYPE_CHECKING:
    from apps.ai.domain.repositories import AiConfigRepository


class GetAiConfigUseCase:
    def __init__(self, ai_config_repo: AiConfigRepository) -> None:
        self._repo = ai_config_repo

    def execute(self, user_id: int) -> AiConfigDTO:
        entity = self._repo.find_by_user_id(user_id)
        if entity is None:
            return AiConfigDTO(
                provider="openai",
                model="gpt-4o-mini",
                is_enabled=False,
                has_api_key=False,
            )
        return AiConfigDTO(
            provider=entity.provider,
            model=entity.model,
            is_enabled=entity.is_enabled,
            has_api_key=bool(entity.api_key),
            updated_at=entity.updated_at,
        )
