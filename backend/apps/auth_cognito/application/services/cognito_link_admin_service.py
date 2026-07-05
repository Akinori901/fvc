"""管理者による m_cognito_links 削除サービス。

Google アカウント差し替え等で「auth_user に紐付いた古い sub」を消すための用途。
削除後、ユーザーが新しい identity でログインすれば JIT が allowed_emails 経由で
新規 link を作る。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.domain.repositories import CognitoLinkRepository


class CognitoLinkAdminService:
    def __init__(self, link_repo: CognitoLinkRepository) -> None:
        self._link_repo = link_repo

    def delete(self, link_id: int, user_id: int) -> None:
        link = self._link_repo.find_by_id(link_id)
        if link is None:
            msg = f"link_id {link_id} のレコードが存在しません"
            raise ValueError(msg)
        if link.user_id != user_id:
            msg = f"link_id {link_id} は user_id {user_id} に属していません"
            raise ValueError(msg)
        self._link_repo.delete(link_id)
