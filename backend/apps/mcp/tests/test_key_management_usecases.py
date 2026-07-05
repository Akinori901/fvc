"""キー管理 4 UseCase の単体テスト（依存はモック）。"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.mcp.application.usecases.authenticate_api_key_usecase import (
    AuthenticateApiKeyUseCase,
)
from apps.mcp.application.usecases.issue_api_key_usecase import IssueApiKeyUseCase
from apps.mcp.application.usecases.list_api_keys_usecase import ListApiKeysUseCase
from apps.mcp.application.usecases.revoke_api_key_usecase import RevokeApiKeyUseCase
from apps.mcp.domain.entities import McpApiKeyEntity
from apps.mcp.domain.exceptions import McpApiKeyNotFoundError


@pytest.fixture(autouse=True)
def _noop_atomic():  # type: ignore[no-untyped-def]
    """transaction.atomic を no-op context manager にして DB アクセスを回避する。"""
    from contextlib import contextmanager

    @contextmanager
    def noop():  # type: ignore[no-untyped-def]
        yield

    targets = [
        "apps.mcp.application.usecases.issue_api_key_usecase.transaction.atomic",
        "apps.mcp.application.usecases.revoke_api_key_usecase.transaction.atomic",
    ]
    patchers = [patch(t, side_effect=lambda: noop()) for t in targets]
    for p in patchers:
        p.start()
    try:
        yield
    finally:
        for p in patchers:
            p.stop()


class TestIssueApiKeyUseCase:
    def test_returns_plain_key_in_dto(self) -> None:
        gen = MagicMock()
        gen.generate.return_value = ("fvc_mcp_xxx", "fvc_mcp_", "$2b$hash")
        repo = MagicMock()
        repo.save.return_value = McpApiKeyEntity(
            id=1,
            user_id=99,
            label="Test",
            key_prefix="fvc_mcp_",
            key_hash="$2b$hash",
            created_at=datetime(2026, 5, 13, tzinfo=UTC),
        )
        usecase = IssueApiKeyUseCase(api_key_repo=repo, generator=gen)
        result = usecase.execute(user_id=99, label="Test")
        assert result.plain_key == "fvc_mcp_xxx"
        assert result.label == "Test"

    def test_default_label_when_blank(self) -> None:
        gen = MagicMock()
        gen.generate.return_value = ("fvc_mcp_yyy", "fvc_mcp_", "$2b$h")
        repo = MagicMock()
        saved = McpApiKeyEntity(
            id=2, user_id=1, label="Unnamed", key_prefix="fvc_mcp_", key_hash="h", created_at=datetime.now(tz=UTC)
        )
        repo.save.return_value = saved
        usecase = IssueApiKeyUseCase(api_key_repo=repo, generator=gen)
        result = usecase.execute(user_id=1, label="   ")
        assert result.label == "Unnamed"


class TestRevokeApiKeyUseCase:
    def test_revoke_success(self) -> None:
        repo = MagicMock()
        repo.revoke.return_value = True
        usecase = RevokeApiKeyUseCase(api_key_repo=repo)
        usecase.execute(key_id=5, user_id=99)
        repo.revoke.assert_called_once_with(5, 99)

    def test_revoke_not_found_raises(self) -> None:
        repo = MagicMock()
        repo.revoke.return_value = False
        usecase = RevokeApiKeyUseCase(api_key_repo=repo)
        with pytest.raises(McpApiKeyNotFoundError):
            usecase.execute(key_id=999, user_id=99)


class TestListApiKeysUseCase:
    def test_empty_list(self) -> None:
        repo = MagicMock()
        repo.find_by_user.return_value = []
        usecase = ListApiKeysUseCase(api_key_repo=repo)
        result = usecase.execute(user_id=1)
        assert result == []

    def test_filters_entities_without_id_or_created_at(self) -> None:
        repo = MagicMock()
        valid = McpApiKeyEntity(
            id=1, user_id=1, label="ok", key_prefix="p", key_hash="h", created_at=datetime.now(tz=UTC)
        )
        invalid = McpApiKeyEntity(id=None, user_id=1, label="x", key_prefix="p", key_hash="h")
        repo.find_by_user.return_value = [valid, invalid]
        usecase = ListApiKeysUseCase(api_key_repo=repo)
        result = usecase.execute(user_id=1)
        assert len(result) == 1
        assert result[0].id == 1


class TestAuthenticateApiKeyUseCase:
    def test_empty_key_returns_none(self) -> None:
        usecase = AuthenticateApiKeyUseCase(api_key_repo=MagicMock(), generator=MagicMock())
        assert usecase.execute("") is None

    def test_no_candidates_returns_none(self) -> None:
        gen = MagicMock()
        gen.extract_prefix.return_value = "fvc_mcp_"
        repo = MagicMock()
        repo.find_active_by_prefix.return_value = []
        usecase = AuthenticateApiKeyUseCase(api_key_repo=repo, generator=gen)
        assert usecase.execute("fvc_mcp_unknown") is None

    def test_bcrypt_mismatch_returns_none(self) -> None:
        gen = MagicMock()
        gen.extract_prefix.return_value = "fvc_mcp_"
        gen.verify.return_value = False
        repo = MagicMock()
        repo.find_active_by_prefix.return_value = [
            McpApiKeyEntity(id=1, user_id=1, label="x", key_prefix="fvc_mcp_", key_hash="h")
        ]
        usecase = AuthenticateApiKeyUseCase(api_key_repo=repo, generator=gen)
        assert usecase.execute("fvc_mcp_xxx") is None

    def test_success_updates_last_used(self) -> None:
        gen = MagicMock()
        gen.extract_prefix.return_value = "fvc_mcp_"
        gen.verify.return_value = True
        entity = McpApiKeyEntity(id=42, user_id=7, label="x", key_prefix="fvc_mcp_", key_hash="h", is_active=True)
        repo = MagicMock()
        repo.find_active_by_prefix.return_value = [entity]

        fake_user = MagicMock()
        fake_user.pk = 7
        fake_user.is_active = True

        with patch("apps.mcp.application.usecases.authenticate_api_key_usecase.get_user_model") as mock_get_user_model:
            mock_get_user_model.return_value.objects.filter.return_value.first.return_value = fake_user
            usecase = AuthenticateApiKeyUseCase(api_key_repo=repo, generator=gen)
            user = usecase.execute("fvc_mcp_xxx")
        assert user is fake_user
        repo.update_last_used.assert_called_once_with(42)
