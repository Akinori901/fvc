"""金融目標ORMモデル。"""

from django.conf import settings
from django.db import models


class FinancialGoal(models.Model):
    """金融目標マスタ。

    scope_type:
      - "family": 家族合計（family_total に含むメンバー全員）
      - "members": r_goal_members で紐づく特定メンバーの組み合わせ
    """

    SCOPE_CHOICES = [
        ("family", "家族合計"),
        ("members", "メンバー指定"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="goals",
        verbose_name="ユーザー",
    )
    name = models.CharField("目標名", max_length=100)
    target_value_jpy = models.DecimalField("目標金額(円)", max_digits=16, decimal_places=0)
    target_date = models.DateField("達成目標日（月初固定）")
    scope_type = models.CharField("スコープ種別", max_length=20, choices=SCOPE_CHOICES)
    is_active = models.BooleanField("有効", default=True)
    display_order = models.IntegerField("表示順", default=0)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_financial_goals"
        verbose_name = "金融目標"
        verbose_name_plural = "金融目標"
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return f"{self.user.username} / {self.name} / ¥{self.target_value_jpy:,}"


class GoalMember(models.Model):
    """目標とメンバーの中間テーブル（scope_type="members" 時のみ使用）。"""

    goal = models.ForeignKey(
        FinancialGoal,
        on_delete=models.CASCADE,
        related_name="member_links",
    )
    family_member = models.ForeignKey(
        "portfolios.FamilyMember",
        on_delete=models.CASCADE,
    )

    class Meta:
        db_table = "r_goal_members"
        unique_together = [["goal", "family_member"]]
        verbose_name = "目標メンバー"
        verbose_name_plural = "目標メンバー"

    def __str__(self) -> str:
        return f"{self.goal.name} - {self.family_member.name}"
