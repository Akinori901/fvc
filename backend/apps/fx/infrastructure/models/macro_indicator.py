"""マクロ指標 ORM モデル。"""

from django.db import models


class MacroIndicator(models.Model):
    """マクロ経済指標マスタ（PPP等、年次）"""

    indicator_type = models.CharField("指標種別", max_length=30)  # "PPP_USDJPY"
    year = models.IntegerField("年")
    value = models.DecimalField("値", max_digits=12, decimal_places=4)
    source = models.CharField("ソース", max_length=30, default="OECD")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_macro_indicators"
        unique_together = [["indicator_type", "year"]]
        ordering = ["-year"]
        verbose_name = "マクロ指標"
        verbose_name_plural = "マクロ指標"

    def __str__(self) -> str:
        return f"{self.indicator_type} {self.year} {self.value}"
