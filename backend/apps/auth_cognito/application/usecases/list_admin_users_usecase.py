"""管理者向け auth_user 一覧 UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.application.dto import AdminUserRow
    from apps.auth_cognito.application.services.admin_user_query_service import (
        AdminUserQueryService,
    )


class ListAdminUsersUseCase:
    def __init__(self, admin_user_query_service: AdminUserQueryService) -> None:
        self._service = admin_user_query_service

    def execute(self) -> list[AdminUserRow]:
        return self._service.list_users_with_details()
