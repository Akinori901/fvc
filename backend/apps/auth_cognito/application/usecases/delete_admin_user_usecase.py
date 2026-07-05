"""auth_user を完全削除する UseCase。

CASCADE で m_cognito_links / m_user_allowed_emails / portfolio 等の関連
レコードも消える。self-delete のガードは View 層責務とし、本 UseCase は
そのまま service.delete に委譲する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.admin_user_lifecycle_service import (
        AdminUserLifecycleService,
    )


class DeleteAdminUserUseCase:
    def __init__(self, lifecycle_service: AdminUserLifecycleService) -> None:
        self._service = lifecycle_service

    @transaction.atomic
    def execute(self, user_id: int) -> None:
        self._service.delete(user_id)
