"""チャットメッセージ ORM モデル。

Function Calling のツール呼び出しも 1 レコードずつ保存する。
"""

from django.db import models


class ChatMessage(models.Model):
    """セッション内のメッセージ。

    role:
      - "user": ユーザー入力
      - "assistant": LLM の応答（最終回答 or tool_calls 中間応答）
      - "tool": ツール実行結果
    """

    ROLE_CHOICES = [
        ("user", "ユーザー"),
        ("assistant", "アシスタント"),
        ("tool", "ツール実行結果"),
    ]

    PROVIDER_CHOICES = [
        ("gemini", "Google Gemini (BYOK)"),
        ("openai", "OpenAI (BYOK)"),
        ("openai_admin", "OpenAI (管理者ロール)"),
    ]

    session = models.ForeignKey(
        "chat.ChatSession",
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="セッション",
    )
    role = models.CharField("ロール", max_length=20, choices=ROLE_CHOICES)
    content = models.TextField("内容", blank=True, default="")
    tool_name = models.CharField("ツール名", max_length=100, blank=True, default="")
    tool_args = models.JSONField("ツール引数", default=dict, blank=True)
    tool_result = models.JSONField("ツール実行結果", default=dict, blank=True)
    prompt_tokens = models.IntegerField("プロンプトトークン数", default=0)
    completion_tokens = models.IntegerField("補完トークン数", default=0)
    model_used = models.CharField("使用モデル", max_length=100, blank=True, default="")
    provider = models.CharField(
        "プロバイダー",
        max_length=20,
        choices=PROVIDER_CHOICES,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_chat_messages"
        ordering = ["created_at"]
        verbose_name = "チャットメッセージ"
        verbose_name_plural = "チャットメッセージ"
        indexes = [
            # 日次安全弁: ユーザーごとの role='user' を期間集計
            models.Index(fields=["session", "role", "-created_at"]),
        ]

    def __str__(self) -> str:
        snippet = self.content[:30] if self.content else f"[{self.tool_name}]"
        return f"{self.session_id} / {self.role} / {snippet}"
