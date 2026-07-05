"""為替レート ORM モデル。"""

from django.db import models


class FxRate(models.Model):
    """為替レート日次データ"""

    pair = models.CharField("通貨ペア", max_length=10, default="USDJPY")
    date = models.DateField("日付")
    close_rate = models.DecimalField("終値", max_digits=12, decimal_places=4)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_fx_rates"
        unique_together = [["pair", "date"]]
        ordering = ["-date"]
        verbose_name = "為替レート"
        verbose_name_plural = "為替レート"

    def __str__(self) -> str:
        return f"{self.pair} {self.date} {self.close_rate}"
