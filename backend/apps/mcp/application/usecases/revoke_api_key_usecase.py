"""API キー失効ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from ...domain.exceptions import McpApiKeyNotFoundError

if TYPE_CHECKING:
    from ...domain.repositories import McpApiKeyRepository


class RevokeApiKeyUseCase:
    """指定 user_id 所有の有効な API キーを失効させる。"""

    def __init__(self, api_key_repo: McpApiKeyRepository) -> None:
        self._api_key_repo = api_key_repo

    def execute(self, *, key_id: int, user_id: int) -> None:
        with transaction.atomic():
            revoked = self._api_key_repo.revoke(key_id, user_id)
            if not revoked:
                raise McpApiKeyNotFoundError(f"API キー (id={key_id}) が見つからない、または既に失効しています")
