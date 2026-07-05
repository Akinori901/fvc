"""auth_user に対する許可 email 管理サービス。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from apps.auth_cognito.application.dto import UserAllowedEmailInfo
from apps.auth_cognito.domain.entities import UserAllowedEmailEntity

if TYPE_CHECKING:
    from apps.auth_cognito.domain.repositories import UserAllowedEmailRepository


class AllowedEmailService:
    def __init__(self, allowed_repo: UserAllowedEmailRepository) -> None:
        self._repo = allowed_repo

    def add(self, user_id: int, email: str, label: str = "") -> UserAllowedEmailInfo:
        email_norm = email.strip().lower()
        if not email_norm:
            msg = "email は必須です"
            raise ValueError(msg)

        # auth_user 存在確認
        user_model = get_user_model()
        if not user_model._default_manager.filter(pk=user_id).exists():  # noqa: SLF001
            msg = f"user_id {user_id} のユーザーが存在しません"
            raise ValueError(msg)

        # email 重複チェック (m_user_allowed_emails.email は unique)
        if self._repo.find_by_email(email_norm) is not None:
            msg = f"email {email_norm} は既に他で許可登録されています"
            raise ValueError(msg)

        saved = self._repo.save(UserAllowedEmailEntity(user_id=user_id, email=email_norm, label=label))
        return UserAllowedEmailInfo(
            id=saved.id if saved.id is not None else 0,
            email=saved.email,
            label=saved.label,
        )

    def remove(self, allowed_id: int, user_id: int) -> None:
        allowed = self._repo.find_by_id(allowed_id)
        if allowed is None:
            msg = f"allowed_id {allowed_id} のレコードが存在しません"
            raise ValueError(msg)
        if allowed.user_id != user_id:
            msg = f"allowed_id {allowed_id} は user_id {user_id} に属していません"
            raise ValueError(msg)
        self._repo.delete(allowed_id)
