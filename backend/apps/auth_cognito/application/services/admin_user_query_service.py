"""管理者向け auth_user 一覧取得サービス。

auth_user (Django 標準テーブル) と m_cognito_links / m_user_allowed_emails を
結合し、各 user の Cognito 紐付き状態と許可 email 一覧を返す。
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from apps.auth_cognito.application.dto import (
    AdminUserRow,
    CognitoLinkInfo,
    UserAllowedEmailInfo,
)

if TYPE_CHECKING:
    from apps.auth_cognito.domain.entities import (
        CognitoLinkEntity,
        UserAllowedEmailEntity,
    )
    from apps.auth_cognito.domain.repositories import (
        CognitoLinkRepository,
        UserAllowedEmailRepository,
    )


class AdminUserQueryService:
    """auth_user / m_cognito_links / m_user_allowed_emails を結合した管理者向け一覧を返す。"""

    def __init__(
        self,
        cognito_link_repo: CognitoLinkRepository,
        allowed_email_repo: UserAllowedEmailRepository,
    ) -> None:
        self._link_repo = cognito_link_repo
        self._allowed_repo = allowed_email_repo

    def list_users_with_details(self) -> list[AdminUserRow]:
        user_model = get_user_model()
        links_by_user_id: dict[int, list[CognitoLinkEntity]] = defaultdict(list)
        for link in self._link_repo.list_all():
            links_by_user_id[link.user_id].append(link)
        emails_by_user_id: dict[int, list[UserAllowedEmailEntity]] = defaultdict(list)
        for allowed in self._allowed_repo.list_all():
            emails_by_user_id[allowed.user_id].append(allowed)

        rows: list[AdminUserRow] = []
        # SLF001: get_user_model() の _default_manager を使うのは他箇所と同じ運用
        for user in user_model._default_manager.all().order_by("id"):  # noqa: SLF001
            rows.append(
                AdminUserRow(
                    id=user.pk,
                    email=user.email,
                    username=user.username,
                    is_superuser=bool(user.is_superuser),
                    is_staff=bool(user.is_staff),
                    is_active=bool(user.is_active),
                    date_joined=user.date_joined,
                    last_login=user.last_login,
                    cognito_links=[
                        CognitoLinkInfo(
                            id=link.id if link.id is not None else 0,
                            cognito_sub=link.cognito_sub,
                            provider=link.provider,
                            cognito_email=link.cognito_email,
                            last_signed_in_at=link.last_signed_in_at,
                        )
                        for link in links_by_user_id.get(user.pk, [])
                    ],
                    allowed_emails=[
                        UserAllowedEmailInfo(
                            id=allowed.id if allowed.id is not None else 0,
                            email=allowed.email,
                            label=allowed.label,
                        )
                        for allowed in emails_by_user_id.get(user.pk, [])
                    ],
                )
            )
        return rows
