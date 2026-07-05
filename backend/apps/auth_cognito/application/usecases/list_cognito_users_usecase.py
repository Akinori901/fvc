"""Cognito User Pool ユーザー一覧 + auth_user 紐付き状況 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.auth_cognito.application.dto import CognitoUserRow

if TYPE_CHECKING:
    from apps.auth_cognito.domain.repositories import (
        CognitoLinkRepository,
        CognitoUserPoolRepository,
    )


class ListCognitoUsersUseCase:
    def __init__(
        self,
        cognito_userpool_repo: CognitoUserPoolRepository,
        cognito_link_repo: CognitoLinkRepository,
    ) -> None:
        self._userpool_repo = cognito_userpool_repo
        self._link_repo = cognito_link_repo

    def execute(self) -> list[CognitoUserRow]:
        users = self._userpool_repo.list_users()
        # m_cognito_links.cognito_sub には JWT の sub claim (UUID) が入る。
        # Cognito User Pool の username は IdP 経由だと "Google_xxx" 形式で
        # JWT.sub と一致しないため、必ず sub 属性で引く。
        rows: list[CognitoUserRow] = []
        for user in users:
            link = self._link_repo.find_by_sub(user.sub) if user.sub else None
            rows.append(
                CognitoUserRow(
                    username=user.username,
                    email=user.email,
                    status=user.status,
                    enabled=user.enabled,
                    user_create_date=user.user_create_date,
                    user_last_modified_date=user.user_last_modified_date,
                    identity_provider=user.identity_provider,
                    linked_user_id=link.user_id if link is not None else None,
                )
            )
        return rows
