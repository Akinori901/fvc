"""管理者による auth_user 新規作成 UseCase。

DB 側 (auth_user + m_user_allowed_emails) を `@transaction.atomic` で作成し、
コミット成功後に Cognito `admin_create_user` を呼んで招待メールを送る
(outbox-lite パターン)。Cognito 呼び出し失敗時は warning ログ + フラグ False を返し、
DB はロールバックしない。再送は将来追加する想定 (TODO 参照)。
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from django.db import transaction

from apps.auth_cognito.domain.exceptions import CognitoUserAlreadyExistsError

if TYPE_CHECKING:
    from apps.auth_cognito.application.dto import AdminUserRow, CreateAdminUserDTO
    from apps.auth_cognito.application.services.admin_user_create_service import (
        AdminUserCreateService,
    )
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )
    from apps.auth_cognito.application.services.cognito_invite_service import (
        CognitoInviteService,
    )

logger = logging.getLogger(__name__)


class CreateAdminUserUseCase:
    def __init__(
        self,
        admin_user_create_service: AdminUserCreateService,
        allowed_email_service: AllowedEmailService,
        invite_service: CognitoInviteService,
    ) -> None:
        self._create_service = admin_user_create_service
        self._allowed_service = allowed_email_service
        self._invite_service = invite_service

    def execute(self, dto: CreateAdminUserDTO) -> AdminUserRow:
        row = self._create_in_db(dto)

        # DB コミット後に Cognito 招待メールを送る。失敗時は警告ログ + フラグ False で返す
        # (DB はロールバックしない — auth_user を残せば管理者が再送できる)。
        # TODO(invite-resend): /api/admin/users/{id}/resend-invite/ で再送できるようにする。
        invite_sent = True
        try:
            self._invite_service.invite(dto.email)
        except CognitoUserAlreadyExistsError:
            logger.warning("Cognito user already exists for %s; skip invite mail", dto.email)
            invite_sent = False
        except Exception:  # noqa: BLE001
            logger.exception("Cognito admin_create_user failed for %s", dto.email)
            invite_sent = False

        return replace(row, invite_email_sent=invite_sent)

    @transaction.atomic
    def _create_in_db(self, dto: CreateAdminUserDTO) -> AdminUserRow:
        row = self._create_service.create_user(dto.email)
        allowed = self._allowed_service.add(row.id, dto.email)
        return replace(row, allowed_emails=[allowed])
