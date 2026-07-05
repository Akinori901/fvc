"""API キー一覧ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..dto import ApiKeySummaryDTO

if TYPE_CHECKING:
    from ...domain.repositories import McpApiKeyRepository


class ListApiKeysUseCase:
    """ユーザーが発行した API キーの一覧（平文は含まない）。"""

    def __init__(self, api_key_repo: McpApiKeyRepository) -> None:
        self._api_key_repo = api_key_repo

    def execute(self, *, user_id: int) -> list[ApiKeySummaryDTO]:
        entities = self._api_key_repo.find_by_user(user_id)
        results: list[ApiKeySummaryDTO] = []
        for e in entities:
            if e.id is None or e.created_at is None:
                continue
            results.append(
                ApiKeySummaryDTO(
                    id=e.id,
                    label=e.label,
                    key_prefix=e.key_prefix,
                    is_active=e.is_active,
                    last_used_at=e.last_used_at,
                    created_at=e.created_at,
                )
            )
        return results
