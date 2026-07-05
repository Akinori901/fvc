"""MCP API キー ORM モデル。"""

from django.conf import settings
from django.db import models


class McpApiKey(models.Model):
    """外部 AI クライアント（Claude Desktop / ChatGPT 等）向けの API キー。

    キー形式: `fvc_mcp_<32文字ランダム>`
    DB には `key_prefix`（先頭 8 文字、検索用）と `key_hash`（bcrypt）を保存し、
    平文キーは発行直後のみ呼び出し側に返す。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mcp_api_keys",
        verbose_name="ユーザー",
    )
    label = models.CharField("ラベル", max_length=100, default="")
    key_prefix = models.CharField("キー識別 prefix", max_length=20)
    key_hash = models.CharField("キー bcrypt ハッシュ", max_length=128)
    is_active = models.BooleanField("有効", default=True)
    last_used_at = models.DateTimeField("最終利用日時", null=True, blank=True)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_mcp_api_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key_prefix", "is_active"], name="idx_mcp_key_prefix"),
            models.Index(fields=["user", "is_active"], name="idx_mcp_key_user"),
        ]
        verbose_name = "MCP APIキー"
        verbose_name_plural = "MCP APIキー"

    def __str__(self) -> str:
        return f"{self.user.username} / {self.label} ({self.key_prefix}...)"
