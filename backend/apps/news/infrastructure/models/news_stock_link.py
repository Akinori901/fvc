"""ニュース × 銘柄リンク ORM モデル。"""

from django.db import models


class NewsStockLink(models.Model):
    """ニュースと銘柄の多対多中間テーブル"""

    MATCHED_BY_CHOICES = [
        ("name_exact_with_context", "銘柄名一致+共起語"),
        ("name_exact", "銘柄名一致"),
        ("ticker", "ティッカー一致"),
        ("name_partial", "銘柄名部分一致"),
        ("ai_inferred", "AI推定"),
    ]

    news = models.ForeignKey(
        "news.NewsArticle",
        on_delete=models.CASCADE,
        related_name="stock_links",
        verbose_name="ニュース",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        related_name="news_links",
        verbose_name="銘柄",
    )
    relevance_score = models.DecimalField(
        "関連度スコア",
        max_digits=4,
        decimal_places=2,
    )
    matched_by = models.CharField(
        "マッチ種別",
        max_length=30,
        choices=MATCHED_BY_CHOICES,
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "r_news_stocks"
        unique_together = [["news", "stock"]]
        indexes = [
            models.Index(fields=["stock", "news"], name="idx_news_stock_link"),
        ]
        verbose_name = "ニュース銘柄リンク"
        verbose_name_plural = "ニュース銘柄リンク"

    def __str__(self) -> str:
        return f"news#{self.news_id} <-> stock#{self.stock_id} ({self.relevance_score})"
