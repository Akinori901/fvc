"""ニュース検索キーワード ORM モデル（市場・FX 用、Phase 2 で本格利用）。"""

from django.db import models


class NewsKeyword(models.Model):
    """市場・FX 用 Google News 検索キーワード"""

    CATEGORY_CHOICES = [
        ("market", "市場・マクロ"),
        ("fx", "FX・為替"),
    ]

    category = models.CharField("カテゴリ", max_length=20, choices=CATEGORY_CHOICES)
    keyword = models.CharField("キーワード名", max_length=100)
    query = models.CharField("検索クエリ", max_length=255)
    is_active = models.BooleanField("有効", default=True)
    sort_order = models.IntegerField("並び順", default=0)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_news_keywords"
        ordering = ["category", "sort_order"]
        unique_together = [["category", "keyword"]]
        verbose_name = "ニュース検索キーワード"
        verbose_name_plural = "ニュース検索キーワード"

    def __str__(self) -> str:
        return f"[{self.category}] {self.keyword}"
