"""Cognito link 削除 UseCase (admin)。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.cognito_link_admin_service import (
        CognitoLinkAdminService,
    )


class DeleteCognitoLinkUseCase:
    def __init__(self, cognito_link_admin_service: CognitoLinkAdminService) -> None:
        self._service = cognito_link_admin_service

    @transaction.atomic
    def execute(self, link_id: int, user_id: int) -> None:
        self._service.delete(link_id=link_id, user_id=user_id)
