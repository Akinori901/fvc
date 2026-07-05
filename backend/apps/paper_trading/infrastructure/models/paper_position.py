"""仮想売買ポジションORMモデル。"""

from decimal import Decimal

from django.conf import settings
from django.db import models


class PaperPosition(models.Model):
    """ユーザー×銘柄ごとのポジション集計。売買のたびに更新される。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="paper_positions",
        verbose_name="ユーザー",
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        related_name="paper_positions",
        verbose_name="銘柄",
    )
    quantity = models.PositiveIntegerField("保有数", default=0)
    total_cost = models.DecimalField("総取得コスト", max_digits=14, decimal_places=2, default=Decimal("0"))
    avg_cost_price = models.DecimalField("平均取得単価", max_digits=12, decimal_places=2, default=Decimal("0"))
    realized_profit_total = models.DecimalField("累積確定損益", max_digits=14, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "t_paper_positions"
        unique_together = [("user", "stock")]
        verbose_name = "仮想売買ポジション"
        verbose_name_plural = "仮想売買ポジション"

    def __str__(self) -> str:
        return f"{self.user_id} {self.stock_id} x{self.quantity}"
