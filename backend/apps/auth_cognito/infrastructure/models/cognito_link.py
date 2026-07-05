"""Cognito sub と Django auth_user の紐付け ORM モデル。"""

from django.conf import settings
from django.db import models


class CognitoLink(models.Model):
    """Cognito の `sub`（不変 UUID）と Django User を紐付ける。

    auth_user に列追加するのではなく別テーブルに切り出すことで、
    Django 標準モデルを不可侵に保つ。1 つの auth_user に対し、Cognito の email
    ログインと Google IdP ログインなど複数の sub を紐付けられる ForeignKey 構造。
    """

    PROVIDER_CHOICES = [
        ("cognito", "Cognito (Email/Password)"),
        ("google", "Google"),
    ]

    cognito_sub = models.CharField("Cognito sub", max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cognito_links",
        verbose_name="ユーザー",
    )
    provider = models.CharField(
        "認証プロバイダー",
        max_length=20,
        choices=PROVIDER_CHOICES,
        default="cognito",
    )
    cognito_email = models.EmailField("Cognito email", max_length=254, blank=True, default="")
    last_signed_in_at = models.DateTimeField("最終ログイン日時", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_cognito_links"
        verbose_name = "Cognito 紐付け"
        verbose_name_plural = "Cognito 紐付け"
        indexes = [
            models.Index(fields=["cognito_email"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} / {self.provider} / sub={self.cognito_sub[:8]}…"
