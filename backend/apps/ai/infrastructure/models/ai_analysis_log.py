"""AI分析実行ログORMモデル。"""

from django.conf import settings
from django.db import models


class AiAnalysisLog(models.Model):
    """AI分析の実行ログ。レート制限の判定・履歴参照に使用する。"""

    QUESTION_TYPE_CHOICES = [
        ("pbr_low", "PBR低位の理由"),
        ("investment_risk", "投資リスク"),
        ("growth_outlook", "成長見通し"),
        ("custom", "カスタム質問"),
    ]

    EXPERT_ROLE_CHOICES = [
        ("general", "汎用アナリスト"),
        ("quant", "クオンツ"),
        ("fundamental", "ファンダメンタルズ"),
        ("macro", "マクロ"),
        ("technical", "テクニカル"),
        ("risk_mgmt", "リスク管理"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_analysis_logs",
        verbose_name="ユーザー",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.SET_NULL,
        null=True,
        related_name="ai_analysis_logs",
        verbose_name="銘柄",
    )
    question_type = models.CharField(
        "質問タイプ",
        max_length=30,
        choices=QUESTION_TYPE_CHOICES,
    )
    custom_question = models.TextField(
        "カスタム質問",
        blank=True,
        default="",
    )
    expert_role = models.CharField(
        "専門家ロール",
        max_length=20,
        choices=EXPERT_ROLE_CHOICES,
        default="general",
    )
    model_used = models.CharField("使用モデル", max_length=100)
    prompt_tokens = models.IntegerField("プロンプトトークン数", default=0)
    completion_tokens = models.IntegerField("補完トークン数", default=0)
    is_success = models.BooleanField("成功フラグ", default=True)
    error_message = models.TextField("エラーメッセージ", blank=True, default="")
    created_at = models.DateTimeField("実行日時", auto_now_add=True)

    class Meta:
        db_table = "t_ai_analysis_logs"
        ordering = ["-created_at"]
        verbose_name = "AI分析ログ"
        verbose_name_plural = "AI分析ログ"

    def __str__(self) -> str:
        return f"{self.user.username} / {self.stock_id} / {self.question_type} ({self.created_at})"
