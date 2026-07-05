"""許可 email 追加 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.dto import AddAllowedEmailDTO, UserAllowedEmailInfo
    from apps.auth_cognito.application.services.allowed_email_service import (
        AllowedEmailService,
    )


class AddAllowedEmailUseCase:
    def __init__(self, allowed_email_service: AllowedEmailService) -> None:
        self._service = allowed_email_service

    @transaction.atomic
    def execute(self, dto: AddAllowedEmailDTO) -> UserAllowedEmailInfo:
        return self._service.add(user_id=dto.user_id, email=dto.email, label=dto.label)
