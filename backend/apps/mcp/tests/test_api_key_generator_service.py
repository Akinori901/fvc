"""ApiKeyGeneratorService の単体テスト。"""

from __future__ import annotations

from apps.mcp.application.services.api_key_generator_service import ApiKeyGeneratorService
from apps.mcp.domain.entities import API_KEY_PREFIX_LENGTH, API_KEY_PREFIX_LITERAL


class TestApiKeyGeneratorService:
    def setup_method(self) -> None:
        self.service = ApiKeyGeneratorService()

    def test_generate_returns_triple(self) -> None:
        plain, prefix, key_hash = self.service.generate()
        assert plain.startswith(API_KEY_PREFIX_LITERAL)
        assert len(plain) == API_KEY_PREFIX_LENGTH + 32  # "fvc_mcp_" + 32 chars
        assert prefix == plain[:API_KEY_PREFIX_LENGTH]
        assert key_hash.startswith("$2b$") or key_hash.startswith("$2a$")

    def test_verify_matches(self) -> None:
        plain, _prefix, key_hash = self.service.generate()
        assert self.service.verify(plain, key_hash) is True

    def test_verify_rejects_wrong_key(self) -> None:
        _plain, _prefix, key_hash = self.service.generate()
        assert self.service.verify("fvc_mcp_XYZ_wrong", key_hash) is False

    def test_verify_empty_inputs_return_false(self) -> None:
        assert self.service.verify("", "h") is False
        assert self.service.verify("k", "") is False

    def test_extract_prefix(self) -> None:
        prefix = ApiKeyGeneratorService.extract_prefix("fvc_mcp_abcdef1234567890")
        assert prefix == "fvc_mcp_"

    def test_each_generation_unique(self) -> None:
        plain1, _, _ = self.service.generate()
        plain2, _, _ = self.service.generate()
        assert plain1 != plain2
