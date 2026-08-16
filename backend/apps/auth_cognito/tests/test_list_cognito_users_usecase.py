"""ListCognitoUsersUseCase のテスト。"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.usecases.list_cognito_users_usecase import (
    ListCognitoUsersUseCase,
)
from apps.auth_cognito.domain.entities import CognitoUserInfo
from apps.auth_cognito.domain.repositories import (
    CognitoLinkRepository,
    CognitoUserPoolRepository,
)
from apps.auth_cognito.infrastructure.models import CognitoLink
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoCognitoLinkRepository,
)


class _FakeUserPoolRepo(CognitoUserPoolRepository):
    """`list_users` のみ使うテスト用 Fake。他メソッドは呼ばれないので NotImplemented で防御。"""

    def __init__(self, users: list[CognitoUserInfo]) -> None:
        self._users = users

    def list_users(self) -> list[CognitoUserInfo]:
        return list(self._users)

    def get_user(self, username: str) -> CognitoUserInfo | None:
        raise NotImplementedError

    def disable_user(self, username: str) -> None:
        raise NotImplementedError

    def enable_user(self, username: str) -> None:
        raise NotImplementedError

    def delete_user(self, username: str) -> None:
        raise NotImplementedError

    def admin_create_user(self, email: str) -> None:
        raise NotImplementedError

    def resend_invite(self, email: str) -> None:
        raise NotImplementedError


@pytest.mark.django_db
class TestListCognitoUsersUseCase:
    def test_list_combines_cognito_and_links_with_mock_boto3(self) -> None:
        # 1 ユーザーは link 済み、もう 1 ユーザーは未紐付き
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com"
        )
        CognitoLink.objects.create(
            cognito_sub="alice-sub",
            user=user,
            provider="cognito",
            cognito_email="alice@example.com",
        )

        now = datetime.now(tz=UTC)
        fake_users = [
            CognitoUserInfo(
                username="alice-sub",
                sub="alice-sub",
                email="alice@example.com",
                status="CONFIRMED",
                enabled=True,
                user_create_date=now,
                user_last_modified_date=now,
                identity_provider="Cognito",
            ),
            CognitoUserInfo(
                username="orphan-sub",
                sub="orphan-sub",
                email="orphan@example.com",
                status="CONFIRMED",
                enabled=True,
                user_create_date=now,
                user_last_modified_date=now,
                identity_provider="Cognito",
            ),
        ]
        link_repo: CognitoLinkRepository = DjangoCognitoLinkRepository()
        usecase = ListCognitoUsersUseCase(
            cognito_userpool_repo=_FakeUserPoolRepo(fake_users),
            cognito_link_repo=link_repo,
        )

        rows = usecase.execute()

        assert len(rows) == 2
        by_username = {row.username: row for row in rows}
        assert by_username["alice-sub"].linked_user_id == user.pk
        assert by_username["orphan-sub"].linked_user_id is None

    def test_google_idp_user_resolves_link_via_sub_not_username(self) -> None:
        """Google IdP の username (`Google_xxx`) と sub (UUID) は別物。

        m_cognito_links.cognito_sub には JWT.sub (UUID) が入るため、Cognito 側の
        username で照合すると紐付きが見つからないバグがあった。本テストはその
        regression を防ぐ。
        """
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="akinori", email="akinori@example.com"
        )
        # JIT が link 作成する際の sub (UUID)
        link_sub = "11111111-2222-3333-4444-555555555555"
        CognitoLink.objects.create(
            cognito_sub=link_sub,
            user=user,
            provider="google",
            cognito_email="a.fukugi@gmail.com",
        )

        now = datetime.now(tz=UTC)
        # Cognito ListUsers の Username は "Google_xxx" 形式、sub 属性は UUID
        fake_users = [
            CognitoUserInfo(
                username="Google_105819244000000000000",
                sub=link_sub,
                email="a.fukugi@gmail.com",
                status="EXTERNAL_PROVIDER",
                enabled=True,
                user_create_date=now,
                user_last_modified_date=now,
                identity_provider="Google",
            ),
        ]
        usecase = ListCognitoUsersUseCase(
            cognito_userpool_repo=_FakeUserPoolRepo(fake_users),
            cognito_link_repo=DjangoCognitoLinkRepository(),
        )

        rows = usecase.execute()

        assert len(rows) == 1
        assert rows[0].linked_user_id == user.pk
        assert rows[0].identity_provider == "Google"

    def test_user_without_sub_attribute_returns_unlinked(self) -> None:
        """sub 属性が空のレアケースは紐付きなしとして扱う (find_by_sub をスキップ)。"""
        now = datetime.now(tz=UTC)
        fake_users = [
            CognitoUserInfo(
                username="no-sub-user",
                sub="",
                email="x@example.com",
                status="UNCONFIRMED",
                enabled=True,
                user_create_date=now,
                user_last_modified_date=now,
                identity_provider="Cognito",
            ),
        ]
        usecase = ListCognitoUsersUseCase(
            cognito_userpool_repo=_FakeUserPoolRepo(fake_users),
            cognito_link_repo=DjangoCognitoLinkRepository(),
        )

        rows = usecase.execute()
        assert rows[0].linked_user_id is None
