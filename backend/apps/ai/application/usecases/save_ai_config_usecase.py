"""AI設定保存ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.ai.application.dto import AiConfigDTO
from apps.ai.domain.entities import AiConfigEntity

if TYPE_CHECKING:
    from apps.ai.domain.repositories import AiConfigRepository


class SaveAiConfigUseCase:
    def __init__(self, ai_config_repo: AiConfigRepository) -> None:
        self._repo = ai_config_repo

    def execute(
        self,
        user_id: int,
        provider: str,
        api_key: str | None,
        model: str,
        is_enabled: bool,
    ) -> AiConfigDTO:
        existing = self._repo.find_by_user_id(user_id)

        # api_keyがNoneの場合は既存キーを維持
        resolved_key = api_key if api_key is not None else (existing.api_key if existing else "")

        entity = AiConfigEntity(
            id=existing.id if existing else None,
            user_id=user_id,
            provider=provider,
            api_key=resolved_key,
            model=model,
            is_enabled=is_enabled,
        )
        saved = self._repo.save(entity)

        return AiConfigDTO(
            provider=saved.provider,
            model=saved.model,
            is_enabled=saved.is_enabled,
            has_api_key=bool(saved.api_key),
            updated_at=saved.updated_at,
        )
