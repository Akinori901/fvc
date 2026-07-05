"""金利データ ORM モデル。"""

from django.db import models


class InterestRate(models.Model):
    """金利データ（日次/月次）"""

    country = models.CharField("国コード", max_length=5)  # "US" | "JP"
    rate_type = models.CharField("金利種別", max_length=10, default="10Y")
    date = models.DateField("日付")
    rate = models.DecimalField("金利(%)", max_digits=8, decimal_places=4)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_interest_rates"
        unique_together = [["country", "rate_type", "date"]]
        ordering = ["-date"]
        verbose_name = "金利データ"
        verbose_name_plural = "金利データ"

    def __str__(self) -> str:
        return f"{self.country} {self.rate_type} {self.date} {self.rate}%"
