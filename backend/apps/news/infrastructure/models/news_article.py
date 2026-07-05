"""ニュース記事 ORM モデル。"""

from django.db import models


class NewsArticle(models.Model):
    """ニュース記事本体"""

    CATEGORY_CHOICES = [
        ("stock", "個別銘柄"),
        ("market", "市場・マクロ"),
        ("fx", "FX・為替"),
        ("earnings", "決算・IR"),
    ]

    SOURCE_CHOICES = [
        ("google_news_rss", "Google News RSS"),
        ("yfinance", "yfinance"),
        ("jquants", "J-Quants"),
    ]

    source = models.CharField("ソース", max_length=20, choices=SOURCE_CHOICES)
    source_article_id = models.CharField("ソース内記事ID", max_length=255)
    category = models.CharField("カテゴリ", max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField("タイトル", max_length=500)
    url = models.CharField("記事URL", max_length=1000)
    summary = models.TextField("要約", blank=True, default="")
    publisher = models.CharField("発行元", max_length=100, blank=True, default="")
    language = models.CharField("言語", max_length=5, default="ja")
    published_at = models.DateTimeField("公開日時")
    fetched_at = models.DateTimeField("取り込み日時", auto_now_add=True)
    ai_analyzed_at = models.DateTimeField("AI分析実行日時", null=True, blank=True)
    importance_score = models.DecimalField(
        "重要度スコア",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "t_news_articles"
        ordering = ["-published_at"]
        unique_together = [["source", "source_article_id"]]
        indexes = [
            models.Index(fields=["category", "-published_at"], name="idx_news_cat_pub"),
            models.Index(fields=["-importance_score"], name="idx_news_importance"),
        ]
        verbose_name = "ニュース記事"
        verbose_name_plural = "ニュース記事"

    def __str__(self) -> str:
        return f"{self.category} / {self.title[:50]}"
