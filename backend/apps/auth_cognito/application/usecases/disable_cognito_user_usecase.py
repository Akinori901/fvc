"""Cognito User Pool ユーザーを無効化する UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
        CognitoUserPoolAdminService,
    )


class DisableCognitoUserUseCase:
    def __init__(self, service: CognitoUserPoolAdminService) -> None:
        self._service = service

    def execute(self, username: str) -> None:
        # Cognito API 単独操作なので @transaction.atomic 不要
        self._service.disable(username)
