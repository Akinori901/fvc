from django.conf import settings
from django.db import models

from apps.stocks.models import Stock


class Valuation(models.Model):
    """適正価格算出結果"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="valuations", verbose_name="ユーザー"
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="valuations", verbose_name="銘柄")
    calculated_at = models.DateTimeField("算出日時", auto_now_add=True)
    growth_rate = models.DecimalField("成長率", max_digits=8, decimal_places=4)
    fair_pbr = models.DecimalField("適正PBR", max_digits=8, decimal_places=4)
    fair_value = models.DecimalField("適正株価", max_digits=12, decimal_places=2)
    current_price = models.DecimalField("算出時の現在株価", max_digits=12, decimal_places=2)
    discount_rate = models.DecimalField("割引/割増率", max_digits=8, decimal_places=4)
    is_undervalued = models.BooleanField("割安判定")
    # ゴードン成長モデル追加フィールド（nullable: 旧レコードとの互換性）
    roe = models.DecimalField("使用ROE", max_digits=8, decimal_places=4, null=True, blank=True)
    cost_of_capital = models.DecimalField("資本コスト", max_digits=8, decimal_places=4, null=True, blank=True)
    bps = models.DecimalField("使用BPS", max_digits=12, decimal_places=2, null=True, blank=True)
    current_pbr = models.DecimalField("現在PBR", max_digits=8, decimal_places=4, null=True, blank=True)
    implied_growth_rate = models.DecimalField(
        "市場織り込み成長率", max_digits=8, decimal_places=4, null=True, blank=True
    )
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    class Meta:
        db_table = "t_valuations"
        ordering = ["-calculated_at"]
        verbose_name = "適正価格算出結果"
        verbose_name_plural = "適正価格算出結果"

    def __str__(self) -> str:
        label = "割安" if self.is_undervalued else "割高"
        return f"{self.stock.code} ¥{self.fair_value}({label})"
