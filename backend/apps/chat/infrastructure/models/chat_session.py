"""チャットセッション ORM モデル。"""

from django.conf import settings
from django.db import models


class ChatSession(models.Model):
    """ユーザーのチャットセッション。

    1 ユーザーは複数セッション可。`provider` はセッション開始時の値を保持し、
    途中で AI 設定が変更された場合も履歴整合性のために変えない。
    """

    PROVIDER_CHOICES = [
        ("gemini", "Google Gemini (BYOK)"),
        ("openai", "OpenAI (BYOK)"),
        ("openai_admin", "OpenAI (管理者ロール)"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        verbose_name="ユーザー",
    )
    provider = models.CharField(
        "プロバイダー",
        max_length=20,
        choices=PROVIDER_CHOICES,
    )
    title = models.CharField("タイトル", max_length=200, blank=True, default="")
    started_at = models.DateTimeField("開始日時", auto_now_add=True)
    last_message_at = models.DateTimeField("最終メッセージ日時", auto_now=True)

    class Meta:
        db_table = "t_chat_sessions"
        ordering = ["-last_message_at"]
        verbose_name = "チャットセッション"
        verbose_name_plural = "チャットセッション"
        indexes = [
            models.Index(fields=["user", "-last_message_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} / {self.provider} / {self.started_at:%Y-%m-%d %H:%M}"
