"""auth_user の有効/無効/削除サービス。

削除は CASCADE で関連レコード (m_cognito_links / m_user_allowed_emails /
portfolio 等) すべて消える。self-delete ガード等の認可は View 層責務とし、
本サービスは「指定された user_id」を機械的に処理する。
"""

from __future__ import annotations

from django.contrib.auth import get_user_model


class AdminUserLifecycleService:
    """auth_user の disable / enable / delete を行う。"""

    def disable(self, user_id: int) -> None:
        self._update_active(user_id, is_active=False)

    def enable(self, user_id: int) -> None:
        self._update_active(user_id, is_active=True)

    def delete(self, user_id: int) -> None:
        user_model = get_user_model()
        # 存在チェック (DoesNotExist は明示エラーで上に投げる)
        if not user_model._default_manager.filter(pk=user_id).exists():  # noqa: SLF001
            msg = f"user_id {user_id} のユーザーが存在しません"
            raise ValueError(msg)
        # delete() は CASCADE 起動。m_cognito_links / m_user_allowed_emails / portfolio 等も消える。
        user_model._default_manager.filter(pk=user_id).delete()  # noqa: SLF001

    @staticmethod
    def _update_active(user_id: int, *, is_active: bool) -> None:
        user_model = get_user_model()
        updated = user_model._default_manager.filter(pk=user_id).update(  # noqa: SLF001
            is_active=is_active
        )
        if updated == 0:
            msg = f"user_id {user_id} のユーザーが存在しません"
            raise ValueError(msg)
