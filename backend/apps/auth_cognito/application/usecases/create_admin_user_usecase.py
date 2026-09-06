"""管理者による auth_user 新規作成 UseCase。

DB 側 (auth_user + m_user_allowed_emails) を `@transaction.atomic` で作成する。
同じ email が `m_user_allowed_emails` にも登録されるため、当該 email で
Cognito ログインすると初回 JIT で auth_user に紐付く。招待メール送信は
認証コンソール側の役割であり、本アプリは Cognito User Pool の実体を操作しない。
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.dto import AdminUserRow, CreateAdminUserDTO
    from apps.auth_cognito.application.services.admin_user_create_service import (
        AdminUserCreateService,
    )
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )


class CreateAdminUserUseCase:
    def __init__(
        self,
        admin_user_create_service: AdminUserCreateService,
        allowed_email_service: AllowedEmailService,
    ) -> None:
        self._create_service = admin_user_create_service
        self._allowed_service = allowed_email_service

    @transaction.atomic
    def execute(self, dto: CreateAdminUserDTO) -> AdminUserRow:
        row = self._create_service.create_user(dto.email)
        allowed = self._allowed_service.add(row.id, dto.email)
        return replace(row, allowed_emails=[allowed])
