"""Cognito User Pool ユーザーを有効化する UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
        CognitoUserPoolAdminService,
    )


class EnableCognitoUserUseCase:
    def __init__(self, service: CognitoUserPoolAdminService) -> None:
        self._service = service

    def execute(self, username: str) -> None:
        self._service.enable(username)
