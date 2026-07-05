"""McpApiKeyEntity の単体テスト。"""

from __future__ import annotations

from apps.mcp.domain.entities import API_KEY_PREFIX_LENGTH, API_KEY_PREFIX_LITERAL, McpApiKeyEntity


class TestMcpApiKeyEntity:
    def test_minimum_construction(self) -> None:
        entity = McpApiKeyEntity(
            user_id=1,
            label="Test",
            key_prefix="fvc_mcp_",
            key_hash="$2b$12$xxx",
        )
        assert entity.id is None
        assert entity.is_active is True
        assert entity.last_used_at is None

    def test_prefix_constants(self) -> None:
        assert API_KEY_PREFIX_LITERAL == "fvc_mcp_"
        assert API_KEY_PREFIX_LENGTH == 8

    def test_user_id_required(self) -> None:
        entity = McpApiKeyEntity(user_id=99, label="iOS", key_prefix="fvc_mcp_", key_hash="h")
        assert entity.user_id == 99
