"""CognitoInviteService と Boto3CognitoUserPoolRepository.admin_create_user のテスト。

ネットワークを叩かないよう boto3 client は MagicMock を渡す。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from apps.auth_cognito.application.services.cognito_invite_service import (
    CognitoInviteService,
)
from apps.auth_cognito.domain.exceptions import CognitoUserAlreadyExistsError
from apps.auth_cognito.infrastructure.repositories.boto3_cognito_userpool_repository import (
    Boto3CognitoUserPoolRepository,
)


def _make_repo() -> tuple[Boto3CognitoUserPoolRepository, MagicMock]:
    client = MagicMock()
    repo = Boto3CognitoUserPoolRepository(client=client, user_pool_id="pool-xyz")
    return repo, client


class TestBoto3AdminCreateUser:
    def test_admin_create_user_calls_boto3_with_expected_args(self) -> None:
        repo, client = _make_repo()

        repo.admin_create_user(email="new@example.com")

        client.admin_create_user.assert_called_once()
        kwargs = client.admin_create_user.call_args.kwargs
        assert kwargs["UserPoolId"] == "pool-xyz"
        assert kwargs["Username"] == "new@example.com"
        assert kwargs["DesiredDeliveryMediums"] == ["EMAIL"]
        # email + email_verified=true を必ず渡す
        attrs = {a["Name"]: a["Value"] for a in kwargs["UserAttributes"]}
        assert attrs == {"email": "new@example.com", "email_verified": "true"}
        # TemporaryPassword は指定しない (Cognito 自動生成)
        assert "TemporaryPassword" not in kwargs
        # MessageAction も指定しない (= デフォルトで invite 送信)
        assert "MessageAction" not in kwargs

    def test_admin_create_user_converts_username_exists_exception(self) -> None:
        repo, client = _make_repo()

        class _UsernameExistsError(Exception):
            pass

        client.exceptions.UsernameExistsException = _UsernameExistsError
        client.admin_create_user.side_effect = _UsernameExistsError("already exists")

        with pytest.raises(CognitoUserAlreadyExistsError) as exc_info:
            repo.admin_create_user(email="dup@example.com")
        assert exc_info.value.email == "dup@example.com"


class _FakeRepo:
    def __init__(self, raises: Exception | None = None) -> None:
        self.calls: list[str] = []
        self._raises = raises

    def admin_create_user(self, email: str) -> None:
        self.calls.append(email)
        if self._raises is not None:
            raise self._raises


class TestCognitoInviteService:
    def test_invite_delegates_to_repository(self) -> None:
        fake = _FakeRepo()
        service = CognitoInviteService(userpool_repo=fake)  # type: ignore[arg-type]

        service.invite("a@example.com")

        assert fake.calls == ["a@example.com"]

    def test_invite_propagates_already_exists(self) -> None:
        fake = _FakeRepo(raises=CognitoUserAlreadyExistsError("a@example.com"))
        service = CognitoInviteService(userpool_repo=fake)  # type: ignore[arg-type]

        with pytest.raises(CognitoUserAlreadyExistsError):
            service.invite("a@example.com")
