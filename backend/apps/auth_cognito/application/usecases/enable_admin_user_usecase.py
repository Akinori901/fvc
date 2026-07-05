"""auth_user を有効化する UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.admin_user_lifecycle_service import (
        AdminUserLifecycleService,
    )


class EnableAdminUserUseCase:
    def __init__(self, lifecycle_service: AdminUserLifecycleService) -> None:
        self._service = lifecycle_service

    @transaction.atomic
    def execute(self, user_id: int) -> None:
        self._service.enable(user_id)
