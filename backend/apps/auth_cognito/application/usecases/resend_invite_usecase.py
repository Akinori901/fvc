"""招待メール再送 UseCase。

Cognito に既存ユーザーが存在するかどうかで処理を分岐：
- 存在すれば `resend()` で再送
- 存在しなければ `invite()` で新規招待
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.application.services.cognito_invite_service import CognitoInviteService
    from apps.auth_cognito.infrastructure.repositories.boto3_cognito_userpool_repository import (
        Boto3CognitoUserPoolRepository,
    )


class ResendInviteUseCase:
    def __init__(
        self,
        invite_service: CognitoInviteService,
        userpool_repo: Boto3CognitoUserPoolRepository,
    ) -> None:
        self._invite_service = invite_service
        self._userpool_repo = userpool_repo

    def execute(self, user_id: int) -> None:
        """user_id に対して招待メール再送を実行する。

        Cognito にユーザーが存在すれば RESEND で再送、
        存在しなければ新規招待を試みる。
        """
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        try:
            user = user_model._default_manager.get(pk=user_id)
        except user_model.DoesNotExist as exc:
            raise ValueError(f"user_id {user_id} のユーザーが存在しません") from exc

        cognito_user = self._userpool_repo.get_user(user.email)
        if cognito_user is not None:
            self._invite_service.resend(user.email)
        else:
            self._invite_service.invite(user.email)
