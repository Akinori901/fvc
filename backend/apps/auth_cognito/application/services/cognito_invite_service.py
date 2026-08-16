"""Cognito 招待メール送信サービス。

`admin_create_user` を呼ぶだけの薄いラッパ。UseCase 層が boto3 を直接知らずに
済むよう 1 段噛ませており、テスト時に Fake repository を差し込みやすい。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.auth_cognito.domain.repositories import CognitoUserPoolRepository


class CognitoInviteService:
    def __init__(self, userpool_repo: CognitoUserPoolRepository) -> None:
        self._repo = userpool_repo

    def invite(self, email: str) -> None:
        """Cognito にユーザーを作成して招待メールを送信する。

        既存ユーザーの場合は `CognitoUserAlreadyExistsError` がそのまま伝播する。
        boto3 の `ClientError` 等もそのまま呼び出し側に伝播させる (UseCase で握る)。
        """
        self._repo.admin_create_user(email)

    def resend(self, email: str) -> None:
        """既存(未確認)ユーザーへ招待メールを再送する (MessageAction=RESEND)。"""
        self._repo.resend_invite(email)
