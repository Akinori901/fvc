"""boto3 を使った Cognito User Pool リポジトリ実装。"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from apps.auth_cognito.domain.entities import CognitoUserInfo
from apps.auth_cognito.domain.exceptions import CognitoUserAlreadyExistsError
from apps.auth_cognito.domain.repositories import CognitoUserPoolRepository

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


class Boto3CognitoUserPoolRepository(CognitoUserPoolRepository):
    """Cognito User Pool に対する読取アクセス。

    管理 UI 用に `list_users` のみ実装する。Enable/Disable 等の書込は AWS Console で行う方針。
    """

    # cognito-idp.list_users の Limit 上限は 60。それ以上は NextToken で pagination する。
    _PAGE_LIMIT = 60

    def __init__(self, client: Any, user_pool_id: str) -> None:
        self._client = client
        self._user_pool_id = user_pool_id

    def list_users(self) -> list[CognitoUserInfo]:
        results: list[CognitoUserInfo] = []
        pagination_token: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "UserPoolId": self._user_pool_id,
                "Limit": self._PAGE_LIMIT,
            }
            if pagination_token is not None:
                kwargs["PaginationToken"] = pagination_token
            response = self._client.list_users(**kwargs)
            for raw_user in response.get("Users", []):
                results.append(self._to_entity(raw_user))
            pagination_token = response.get("PaginationToken")
            if not pagination_token:
                break
        return results

    def get_user(self, username: str) -> CognitoUserInfo | None:
        try:
            response = self._client.admin_get_user(
                UserPoolId=self._user_pool_id,
                Username=username,
            )
        except self._client.exceptions.UserNotFoundException:
            return None
        # admin_get_user は list_users とフィールド名が一部違う:
        # - "UserAttributes" (list_users では "Attributes")
        # - top-level に Username / Enabled / UserStatus / UserCreateDate / UserLastModifiedDate
        normalized = {
            "Username": response.get("Username", ""),
            "Attributes": response.get("UserAttributes", []),
            "Enabled": response.get("Enabled", False),
            "UserStatus": response.get("UserStatus", ""),
            "UserCreateDate": response.get("UserCreateDate"),
            "UserLastModifiedDate": response.get("UserLastModifiedDate"),
        }
        return self._to_entity(normalized)

    def disable_user(self, username: str) -> None:
        self._client.admin_disable_user(
            UserPoolId=self._user_pool_id,
            Username=username,
        )

    def enable_user(self, username: str) -> None:
        self._client.admin_enable_user(
            UserPoolId=self._user_pool_id,
            Username=username,
        )

    def delete_user(self, username: str) -> None:
        self._client.admin_delete_user(
            UserPoolId=self._user_pool_id,
            Username=username,
        )

    def admin_create_user(self, email: str) -> None:
        try:
            self._client.admin_create_user(
                UserPoolId=self._user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                ],
                DesiredDeliveryMediums=["EMAIL"],
            )
        except self._client.exceptions.UsernameExistsException as exc:
            raise CognitoUserAlreadyExistsError(email) from exc

    def resend_invite(self, email: str) -> None:
        """既存(未確認)ユーザーへ招待メールを再送する。

        MessageAction=RESEND は admin_create_user を再送専用モードで呼ぶ指定で、
        既存ユーザーでも UsernameExistsException を出さずに仮パスワードの
        招待メールを再送する。
        """
        self._client.admin_create_user(
            UserPoolId=self._user_pool_id,
            Username=email,
            MessageAction="RESEND",
            DesiredDeliveryMediums=["EMAIL"],
        )

    @classmethod
    def _to_entity(cls, raw: dict[str, Any]) -> CognitoUserInfo:
        attrs = cls._attrs_to_dict(raw.get("Attributes", []))
        identity_provider = cls._extract_identity_provider(attrs.get("identities", ""))
        return CognitoUserInfo(
            username=str(raw.get("Username", "")),
            sub=attrs.get("sub", ""),
            email=attrs.get("email", ""),
            status=str(raw.get("UserStatus", "")),
            enabled=bool(raw.get("Enabled", False)),
            user_create_date=cls._coerce_datetime(raw.get("UserCreateDate")),
            user_last_modified_date=cls._coerce_datetime(raw.get("UserLastModifiedDate")),
            identity_provider=identity_provider,
        )

    @staticmethod
    def _attrs_to_dict(attrs: list[dict[str, str]]) -> dict[str, str]:
        return {attr.get("Name", ""): attr.get("Value", "") for attr in attrs}

    @staticmethod
    def _extract_identity_provider(identities_json: str) -> str:
        """`identities` attribute (JSON 配列) から providerName を取り出す。

        フェデレーション (Google 等) の場合のみ identities が入る。空なら "Cognito"。
        """
        if not identities_json:
            return "Cognito"
        try:
            parsed = json.loads(identities_json)
        except (TypeError, ValueError):
            logger.warning("Failed to parse identities JSON: %s", identities_json)
            return "Cognito"
        if not isinstance(parsed, list) or not parsed:
            return "Cognito"
        first = parsed[0]
        if isinstance(first, dict):
            provider = first.get("providerName")
            if isinstance(provider, str) and provider:
                return provider
        return "Cognito"

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        from datetime import datetime as _dt

        if isinstance(value, _dt):
            return value
        return None
