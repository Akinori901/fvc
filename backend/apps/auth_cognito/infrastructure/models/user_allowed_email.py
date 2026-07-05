"""auth_user に対する Cognito ログイン許可 email リスト ORM モデル。"""

from django.conf import settings
from django.db import models


class UserAllowedEmail(models.Model):
    """admin が事前登録する「この auth_user に紐付け可能な email」一覧。

    JIT は JWT.email がここに登録されている場合のみ対応 auth_user に紐付け、
    そうでなければログインを拒否する (招待制を担保)。同じ email を異なる
    auth_user に紐付けることはできない (unique 制約)。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="allowed_emails",
        verbose_name="ユーザー",
    )
    email = models.EmailField("許可 email", max_length=254, unique=True)
    label = models.CharField("ラベル", max_length=100, blank=True, default="")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        db_table = "m_user_allowed_emails"
        verbose_name = "許可 email"
        verbose_name_plural = "許可 email"
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.email} → user_id={self.user_id}"
