"""ユーザーAI設定ORMモデル。"""

from django.conf import settings
from django.db import models


class UserAiConfig(models.Model):
    """ユーザーごとのAI API設定マスタ。

    1ユーザー1レコード（user に OneToOne 制約）。
    provider は現在 "openai" 固定。
    api_key はプレーンテキスト保存。
    """

    PROVIDER_CHOICES = [("gemini", "Google Gemini"), ("openai", "OpenAI")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_config",
        verbose_name="ユーザー",
    )
    provider = models.CharField(
        "プロバイダー",
        max_length=50,
        choices=PROVIDER_CHOICES,
        default="gemini",
    )
    api_key = models.CharField(
        "APIキー",
        max_length=500,
        blank=True,
        default="",
    )
    model = models.CharField(
        "使用モデル",
        max_length=100,
        default="gemini-2.5-flash",
    )
    is_enabled = models.BooleanField("有効フラグ", default=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_user_ai_configs"
        verbose_name = "ユーザーAI設定"
        verbose_name_plural = "ユーザーAI設定"

    def __str__(self) -> str:
        return f"{self.user.username} / {self.provider} / {self.model}"
