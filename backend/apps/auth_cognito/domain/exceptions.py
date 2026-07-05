"""Cognito 認証のドメイン例外。"""

from __future__ import annotations


class CognitoAuthError(Exception):
    """Cognito 認証機能のベース例外。"""


class InvalidCognitoTokenError(CognitoAuthError):
    """JWT の署名・形式・claim 検証に失敗した。

    DRF Authentication Class で `AuthenticationFailed` に変換される。
    """


class CognitoJwksFetchError(CognitoAuthError):
    """JWKS の取得に失敗した（外部接続エラー / 形式エラー）。"""


class UserNotAllowedError(CognitoAuthError):
    """Cognito 認証は成功したが、対応する `auth_user` が事前登録されていない。

    DRF Authentication Class で `AuthenticationFailed` に変換される (401)。
    管理者が事前に `auth_user` を作成しないと利用できない運用を担保する。
    """


class CognitoUserAlreadyExistsError(CognitoAuthError):
    """`admin_create_user` で既に同 username の Cognito ユーザーがいた。"""

    def __init__(self, email: str) -> None:
        super().__init__(f"Cognito user already exists for {email}")
        self.email = email
