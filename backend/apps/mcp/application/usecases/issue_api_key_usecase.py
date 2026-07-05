"""API キー発行ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from ...domain.entities import McpApiKeyEntity
from ..dto import IssuedApiKeyDTO

if TYPE_CHECKING:
    from ...domain.repositories import McpApiKeyRepository
    from ..services.api_key_generator_service import ApiKeyGeneratorService


class IssueApiKeyUseCase:
    """API キー発行: 平文キーは発行直後のみ返却し、DB には bcrypt ハッシュを保存する。"""

    def __init__(
        self,
        api_key_repo: McpApiKeyRepository,
        generator: ApiKeyGeneratorService,
    ) -> None:
        self._api_key_repo = api_key_repo
        self._generator = generator

    def execute(self, *, user_id: int, label: str) -> IssuedApiKeyDTO:
        with transaction.atomic():
            plain_key, key_prefix, key_hash = self._generator.generate()
            entity = McpApiKeyEntity(
                user_id=user_id,
                label=label.strip() or "Unnamed",
                key_prefix=key_prefix,
                key_hash=key_hash,
                is_active=True,
            )
            saved = self._api_key_repo.save(entity)
            if saved.id is None or saved.created_at is None:
                raise RuntimeError("API キーの保存に失敗しました")
            return IssuedApiKeyDTO(
                id=saved.id,
                label=saved.label,
                key_prefix=saved.key_prefix,
                plain_key=plain_key,
                created_at=saved.created_at,
            )
