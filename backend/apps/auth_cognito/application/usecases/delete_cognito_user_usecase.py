"""Cognito User Pool ユーザーを削除する UseCase。

Cognito API 削除と m_cognito_links 同期削除を行う。Cognito API は DB transaction
の外側 (外部 API) のため、本 UseCase では `@transaction.atomic` を使わない。
削除順序と例外処理は CognitoUserPoolAdminService.delete() に集約されている。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.cognito_user_pool_admin_service import (
        CognitoUserPoolAdminService,
    )


class DeleteCognitoUserUseCase:
    def __init__(self, service: CognitoUserPoolAdminService) -> None:
        self._service = service

    def execute(self, username: str) -> None:
        self._service.delete(username)
