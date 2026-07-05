"""仮想売買記録ORMモデル。"""

from django.conf import settings
from django.db import models


class PaperTrade(models.Model):
    """仮想売買記録。イミュータブルな取引ログ。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paper_trades",
        verbose_name="ユーザー",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        related_name="paper_trades",
        verbose_name="銘柄",
    )
    trade_type = models.CharField("売買種別", max_length=4)  # "buy" / "sell"
    quantity = models.PositiveIntegerField("数量")
    price = models.DecimalField("約定単価", max_digits=12, decimal_places=2)
    total_amount = models.DecimalField("約定金額", max_digits=14, decimal_places=2)
    realized_profit = models.DecimalField("確定損益", max_digits=14, decimal_places=2, null=True, blank=True)
    avg_cost_at_trade = models.DecimalField(
        "取引時平均取得単価", max_digits=12, decimal_places=2, null=True, blank=True
    )
    memo = models.CharField("メモ", max_length=200, blank=True, default="")
    traded_at = models.DateTimeField("約定日時")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_paper_trades"
        ordering = ["-traded_at"]
        indexes = [
            models.Index(fields=["user", "stock"]),
        ]
        verbose_name = "仮想売買記録"
        verbose_name_plural = "仮想売買記録"

    def __str__(self) -> str:
        return f"{self.user_id} {self.trade_type} {self.stock_id} x{self.quantity}"
