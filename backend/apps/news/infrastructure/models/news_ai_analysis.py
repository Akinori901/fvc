"""ニュース AI 分析結果 ORM モデル（Phase 2 で本格利用）。"""

from django.conf import settings
from django.db import models


class NewsAiAnalysis(models.Model):
    """ニュースに対する AI 影響分析の結果"""

    IMPACT_DIRECTION_CHOICES = [
        ("positive", "ポジティブ"),
        ("negative", "ネガティブ"),
        ("neutral", "ニュートラル"),
        ("mixed", "混合"),
    ]

    IMPACT_PERIOD_CHOICES = [
        ("short", "短期"),
        ("medium", "中期"),
        ("long", "長期"),
    ]

    CONFIDENCE_CHOICES = [
        ("high", "高"),
        ("medium", "中"),
        ("low", "低"),
    ]

    news = models.ForeignKey(
        "news.NewsArticle",
        on_delete=models.CASCADE,
        related_name="ai_analyses",
        verbose_name="ニュース",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news_ai_analyses",
        verbose_name="ユーザー",
        help_text="NULL = バッチ事前分析, 非NULL = ユーザー要求",
    )
    impact_direction = models.CharField("影響方向", max_length=10, choices=IMPACT_DIRECTION_CHOICES)
    impact_period = models.CharField("影響期間", max_length=10, choices=IMPACT_PERIOD_CHOICES)
    confidence = models.CharField("確度", max_length=10, choices=CONFIDENCE_CHOICES)
    affected_targets = models.JSONField("影響対象", default=list)
    reasoning = models.TextField("分析理由")
    key_points = models.JSONField("要点", default=list)
    model_used = models.CharField("使用モデル", max_length=100)
    prompt_tokens = models.IntegerField("プロンプトトークン数", default=0)
    completion_tokens = models.IntegerField("補完トークン数", default=0)
    generated_at = models.DateTimeField("生成日時")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_news_ai_analyses"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["news", "user"], name="idx_news_ai_news_user"),
        ]
        verbose_name = "ニュースAI分析"
        verbose_name_plural = "ニュースAI分析"

    def __str__(self) -> str:
        return f"news#{self.news_id} {self.impact_direction}/{self.impact_period}"
