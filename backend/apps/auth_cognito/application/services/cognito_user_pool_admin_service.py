"""Cognito User Pool の disable/enable/delete サービス。

delete 時は backend 側の m_cognito_links も同期して削除する (孤児防止)。
sub の解決は削除前に admin_get_user (boto3) で取得。Cognito 削除成功後の
link 削除失敗は best-effort (例外を握り潰してログ警告)。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.domain.repositories import (
        CognitoLinkRepository,
        CognitoUserPoolRepository,
    )

logger = logging.getLogger(__name__)


class CognitoUserPoolAdminService:
    def __init__(
        self,
        userpool_repo: CognitoUserPoolRepository,
        link_repo: CognitoLinkRepository,
    ) -> None:
        self._userpool_repo = userpool_repo
        self._link_repo = link_repo

    def disable(self, username: str) -> None:
        self._userpool_repo.disable_user(username)

    def enable(self, username: str) -> None:
        self._userpool_repo.enable_user(username)

    def delete(self, username: str) -> None:
        # 削除前に sub を取得 (link 同期削除用)
        info = self._userpool_repo.get_user(username)
        sub = info.sub if info is not None else ""

        # Cognito 側削除 (失敗時は例外を上に投げ、link は触らない)
        self._userpool_repo.delete_user(username)

        # link 同期削除 (best-effort: 失敗時はログ警告のみ、Cognito 削除は確定済み)
        if not sub:
            logger.warning("Cognito user %s に sub が無く m_cognito_links 同期削除をスキップしました", username)
            return
        try:
            link = self._link_repo.find_by_sub(sub)
            if link is not None and link.id is not None:
                self._link_repo.delete(link.id)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Cognito user %s 削除後の m_cognito_links 同期削除に失敗 (孤児発生の可能性)",
                username,
                exc_info=True,
            )
