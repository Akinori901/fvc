"""MCP API キーリポジトリ Django ORM 実装。"""

from __future__ import annotations

from datetime import UTC, datetime

from ...domain.entities import McpApiKeyEntity
from ...domain.repositories import McpApiKeyRepository
from ..models import McpApiKey


class DjangoMcpApiKeyRepository(McpApiKeyRepository):
    """Django ORM による MCP API キーリポジトリ実装。"""

    @staticmethod
    def _to_entity(obj: McpApiKey) -> McpApiKeyEntity:
        return McpApiKeyEntity(
            id=obj.pk,
            user_id=obj.user_id,
            label=obj.label,
            key_prefix=obj.key_prefix,
            key_hash=obj.key_hash,
            is_active=obj.is_active,
            last_used_at=obj.last_used_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    def save(self, entity: McpApiKeyEntity) -> McpApiKeyEntity:
        obj = McpApiKey.objects.create(
            user_id=entity.user_id,
            label=entity.label,
            key_prefix=entity.key_prefix,
            key_hash=entity.key_hash,
            is_active=entity.is_active,
        )
        return self._to_entity(obj)

    def find_by_id(self, key_id: int) -> McpApiKeyEntity | None:
        obj = McpApiKey.objects.filter(pk=key_id).first()
        return self._to_entity(obj) if obj else None

    def find_active_by_prefix(self, key_prefix: str) -> list[McpApiKeyEntity]:
        qs = McpApiKey.objects.filter(key_prefix=key_prefix, is_active=True)
        return [self._to_entity(obj) for obj in qs]

    def find_by_user(self, user_id: int) -> list[McpApiKeyEntity]:
        qs = McpApiKey.objects.filter(user_id=user_id).order_by("-created_at")
        return [self._to_entity(obj) for obj in qs]

    def revoke(self, key_id: int, user_id: int) -> bool:
        updated = McpApiKey.objects.filter(pk=key_id, user_id=user_id, is_active=True).update(is_active=False)
        return updated > 0

    def update_last_used(self, key_id: int) -> None:
        McpApiKey.objects.filter(pk=key_id).update(last_used_at=datetime.now(tz=UTC))
