from django.conf import settings
from django.db import models


class AiDecision(models.Model):
    """AI が下した投資判断の履歴。

    Claude / ChatGPT 等の AI クライアントが分析後に save_ai_decision MCP ツールで
    判断結果と当時のスナップショットを保存する。
    """

    class DecisionType(models.TextChoices):
        BUY = "buy", "買い"
        SELL = "sell", "売り"
        HOLD = "hold", "保有継続"
        WATCH = "watch", "ウォッチ"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_decisions",
        verbose_name="ユーザー",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        related_name="ai_decisions",
        verbose_name="銘柄",
    )
    decision_type = models.CharField("判断種別", max_length=20, choices=DecisionType.choices)
    rationale = models.TextField("判断根拠", help_text="AI が生成した自由テキスト")
    confidence = models.DecimalField(
        "確信度",
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="0.00〜1.00（任意）",
    )
    snapshot_indicators = models.JSONField(
        "判断時点のスナップショット",
        default=dict,
        help_text="get_stock_summary 結果のスナップショット",
    )
    ai_model = models.CharField("AI モデル", max_length=100, default="", blank=True)
    decided_at = models.DateTimeField("判断日時", auto_now_add=True)

    class Meta:
        db_table = "t_ai_decisions"
        ordering = ["-decided_at"]
        indexes = [
            models.Index(fields=["user", "-decided_at"], name="idx_aidec_user_decided"),
            models.Index(fields=["stock", "-decided_at"], name="idx_aidec_stock_decided"),
        ]
        verbose_name = "AI 判断履歴"
        verbose_name_plural = "AI 判断履歴"

    def __str__(self) -> str:
        return f"{self.user_id} {self.stock_id} {self.decision_type} {self.decided_at}"
