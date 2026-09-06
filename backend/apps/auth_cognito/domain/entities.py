"""Cognito 認証ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CognitoClaimsEntity:
    """検証済み Cognito JWT のクレーム。

    JWT 署名検証 + claim 検証を通過した後の不変表現。
    DRF 認証〜JIT provisioning の境界で受け渡される。
    """

    sub: str
    client_id: str
    token_use: str  # "access" / "id"
    provider: str  # "cognito" / "google" / ...
    email: str = ""
    name: str = ""
    email_verified: bool = False


@dataclass
class CognitoLinkEntity:
    """Cognito sub と Django User の紐付け。"""

    cognito_sub: str
    user_id: int
    provider: str = "cognito"
    cognito_email: str = ""
    id: int | None = None
    last_signed_in_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class UserAllowedEmailEntity:
    """`m_user_allowed_emails`: 1 auth_user に許可される複数の email。

    admin が事前登録する。Cognito 経由 (Cognito email / Google 等) のログインで
    JWT.email がこの一覧に含まれる場合のみ、対応する auth_user に紐付ける (JIT)。
    """

    user_id: int
    email: str
    label: str = ""
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
