"""許可 email 削除 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )


class RemoveAllowedEmailUseCase:
    def __init__(self, allowed_email_service: AllowedEmailService) -> None:
        self._service = allowed_email_service

    @transaction.atomic
    def execute(self, allowed_id: int, user_id: int) -> None:
        self._service.remove(allowed_id=allowed_id, user_id=user_id)
