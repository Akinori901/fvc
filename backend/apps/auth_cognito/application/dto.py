"""Admin 管理機能 DTO。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CognitoLinkInfo:
    """auth_user に紐付く Cognito link の表示用サマリ (1 user に複数あり得る)。"""

    id: int
    cognito_sub: str
    provider: str
    cognito_email: str
    last_signed_in_at: datetime | None


@dataclass(frozen=True)
class UserAllowedEmailInfo:
    """auth_user に許可されている email の表示用サマリ。"""

    id: int
    email: str
    label: str


@dataclass(frozen=True)
class AdminUserRow:
    """`/api/admin/users/` の 1 行分。

    1 auth_user に対し links / allowed_emails はそれぞれ複数あり得る。
    """

    id: int
    email: str
    username: str
    is_superuser: bool
    is_staff: bool
    is_active: bool
    date_joined: datetime
    last_login: datetime | None
    cognito_links: list[CognitoLinkInfo] = field(default_factory=list)
    allowed_emails: list[UserAllowedEmailInfo] = field(default_factory=list)
    # 新規作成時のみ意味を持つ。Cognito 招待メール送信が成功したか
    # (一覧 GET など、招待を伴わないコンテキストでは常に True で返す)。
    invite_email_sent: bool = True


@dataclass(frozen=True)
class CreateAdminUserDTO:
    email: str


@dataclass(frozen=True)
class AddAllowedEmailDTO:
    user_id: int
    email: str
    label: str = ""


@dataclass(frozen=True)
class CognitoUserRow:
    """`/api/admin/cognito-users/` の 1 行分。"""

    username: str
    email: str
    status: str
    enabled: bool
    user_create_date: datetime | None
    user_last_modified_date: datetime | None
    identity_provider: str
    linked_user_id: int | None
