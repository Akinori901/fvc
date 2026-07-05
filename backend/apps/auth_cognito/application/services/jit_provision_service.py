"""Cognito 認証時の Just-In-Time プロビジョニングサービス。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.auth_cognito.domain.entities import CognitoLinkEntity
from apps.auth_cognito.domain.exceptions import UserNotAllowedError

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

    from apps.auth_cognito.domain.entities import CognitoClaimsEntity
    from apps.auth_cognito.domain.repositories import (
        CognitoLinkRepository,
        UserAllowedEmailRepository,
    )

logger = logging.getLogger(__name__)


class JitProvisionService:
    """初回 Cognito ログイン時に既存 auth_user と m_cognito_links を紐付ける。

    解決順序:
      1. `m_cognito_links.cognito_sub` で既存リンクを検索 → ヒットすればその user を返す
      2. `m_user_allowed_emails` に JWT.email が登録されていればその user に紐付ける
         (1 つの auth_user に Cognito と Google など複数 identity を紐付け可能)
      3. それでも見つからなければ `UserNotAllowedError` を raise (招待制を担保)

    既存ユーザーの `is_superuser` / `is_staff` は変更しない (ロックアウト回避)。
    """

    def __init__(
        self,
        link_repo: CognitoLinkRepository,
        allowed_repo: UserAllowedEmailRepository,
    ) -> None:
        self._link_repo = link_repo
        self._allowed_repo = allowed_repo

    @transaction.atomic
    def provision(self, claims: CognitoClaimsEntity) -> AbstractBaseUser:
        user_model = get_user_model()

        link = self._link_repo.find_by_sub(claims.sub)
        if link is not None:
            existing: AbstractBaseUser = user_model._default_manager.get(pk=link.user_id)  # noqa: SLF001
            return existing

        if not claims.email:
            msg = "Cognito JWT に email claim がありません。管理者に問い合わせてください。"
            raise UserNotAllowedError(msg)

        allowed = self._allowed_repo.find_by_email(claims.email)
        if allowed is None:
            msg = f"email {claims.email} はログインを許可されていません。管理者に許可登録を依頼してください。"
            raise UserNotAllowedError(msg)

        self._link_repo.save(
            CognitoLinkEntity(
                cognito_sub=claims.sub,
                user_id=allowed.user_id,
                provider=claims.provider or "cognito",
                cognito_email=claims.email,
            )
        )
        return user_model._default_manager.get(pk=allowed.user_id)  # noqa: SLF001
