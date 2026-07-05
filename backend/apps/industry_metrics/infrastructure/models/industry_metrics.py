"""業界指標 ORMモデル。"""

from django.db import models


class IndustryMetrics(models.Model):
    """業界平均ROE等の指標マスタ。

    東証33業種ごとに、業界平均ROEのレンジ（下限〜上限）を保持する。
    """

    sector = models.CharField("業種", max_length=100, unique=True)
    min_roe = models.DecimalField("下限ROE", max_digits=8, decimal_places=4)
    max_roe = models.DecimalField("上限ROE", max_digits=8, decimal_places=4)
    note = models.CharField("メモ", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_industry_metrics"
        verbose_name = "業界指標"
        verbose_name_plural = "業界指標"
        ordering = ["sector"]

    def __str__(self) -> str:
        return f"{self.sector} (ROE {self.min_roe}〜{self.max_roe})"
