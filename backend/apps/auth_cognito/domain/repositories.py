"""Cognito 認証のリポジトリ ABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.domain.entities import (
        CognitoLinkEntity,
        CognitoUserInfo,
        UserAllowedEmailEntity,
    )


class CognitoLinkRepository(ABC):
    """`m_cognito_links` の永続化境界。"""

    @abstractmethod
    def find_by_sub(self, cognito_sub: str) -> CognitoLinkEntity | None:
        """Cognito sub から紐付けレコードを取得する。"""

    @abstractmethod
    def find_by_id(self, link_id: int) -> CognitoLinkEntity | None:
        """主キーから紐付けレコードを取得する。"""

    @abstractmethod
    def save(self, link: CognitoLinkEntity) -> CognitoLinkEntity:
        """新規作成 or 更新。`id` が None なら INSERT、それ以外は UPDATE。

        保存後の最新状態を返す。
        """

    @abstractmethod
    def touch_last_signed_in(self, link_id: int) -> None:
        """`last_signed_in_at` を現在時刻で更新する。"""

    @abstractmethod
    def list_all(self) -> list[CognitoLinkEntity]:
        """全紐付けレコードを返す (管理画面の一覧表示用)。"""

    @abstractmethod
    def delete(self, link_id: int) -> None:
        """紐付けレコードを削除する (admin による解除用)。"""


class UserAllowedEmailRepository(ABC):
    """`m_user_allowed_emails` の永続化境界。"""

    @abstractmethod
    def find_by_email(self, email: str) -> UserAllowedEmailEntity | None:
        """email から許可レコードを取得する (大小無視)。"""

    @abstractmethod
    def find_by_id(self, allowed_id: int) -> UserAllowedEmailEntity | None:
        """主キーから許可レコードを取得する。"""

    @abstractmethod
    def list_by_user_id(self, user_id: int) -> list[UserAllowedEmailEntity]:
        """特定 user の許可 email 一覧を返す。"""

    @abstractmethod
    def list_all(self) -> list[UserAllowedEmailEntity]:
        """全許可レコードを返す (管理画面の一覧表示用)。"""

    @abstractmethod
    def save(self, entity: UserAllowedEmailEntity) -> UserAllowedEmailEntity:
        """新規作成 or 更新。`id` が None なら INSERT、それ以外は UPDATE。"""

    @abstractmethod
    def delete(self, allowed_id: int) -> None:
        """許可レコードを削除する。"""


class CognitoUserPoolRepository(ABC):
    """Cognito User Pool そのものへの問い合わせ境界 (管理操作用)。"""

    @abstractmethod
    def list_users(self) -> list[CognitoUserInfo]:
        """User Pool のユーザー一覧を返す。"""

    @abstractmethod
    def get_user(self, username: str) -> CognitoUserInfo | None:
        """指定 username のユーザー情報を取得する。存在しなければ None。"""

    @abstractmethod
    def disable_user(self, username: str) -> None:
        """ユーザーを無効化する (admin_disable_user)。"""

    @abstractmethod
    def enable_user(self, username: str) -> None:
        """ユーザーを有効化する (admin_enable_user)。"""

    @abstractmethod
    def delete_user(self, username: str) -> None:
        """ユーザーを削除する (admin_delete_user)。"""

    @abstractmethod
    def admin_create_user(self, email: str) -> None:
        """Cognito User Pool にユーザーを作成し、招待メール送信をトリガする。

        `Username=email`、`UserAttributes` に `email` と `email_verified=true` を
        セットする。`TemporaryPassword` は指定せず Cognito 自動生成に任せる。
        `DesiredDeliveryMediums=["EMAIL"]`。
        既存ユーザーの場合は `CognitoUserAlreadyExistsError` を raise する。
        """

    @abstractmethod
    def resend_invite(self, email: str) -> None:
        """既存(未確認)ユーザーへ招待メールを再送する (MessageAction=RESEND)。"""
