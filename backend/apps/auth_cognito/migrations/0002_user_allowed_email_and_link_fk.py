"""m_cognito_links.user の OneToOne→ForeignKey 化 +
m_user_allowed_emails 新規作成 + 既存 auth_user.email を allowed_emails に流す
data migration。
"""

from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _populate_allowed_emails_from_existing_users(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
    """既存 auth_user の email を全件 m_user_allowed_emails に投入する。

    Phase D 完了時点で既に sub マッチで紐付き済みのユーザーは引き続き sub マッチで
    認証されるが、将来 Google 等別 identity を追加した際の互換性のため、
    auth_user.email も allowed_emails に最初の 1 行として登録しておく。
    `get_or_create` で冪等性を担保。
    """
    user_model = apps.get_model("auth", "User")
    allowed_model = apps.get_model("auth_cognito", "UserAllowedEmail")
    for user in user_model.objects.exclude(email="").iterator():
        allowed_model.objects.get_or_create(
            email=user.email,
            defaults={"user_id": user.pk, "label": "auth_user.email から自動登録"},
        )


def _noop_reverse(apps, schema_editor) -> None:  # type: ignore[no-untyped-def]
    """ロールバック時は何もしない (allowed_emails テーブル自体は CreateModel の reverse で drop される)。"""


class Migration(migrations.Migration):
    dependencies = [
        ("auth_cognito", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="cognitolink",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cognito_links",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ユーザー",
            ),
        ),
        migrations.CreateModel(
            name="UserAllowedEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="許可 email")),
                ("label", models.CharField(blank=True, default="", max_length=100, verbose_name="ラベル")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="作成日時")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新日時")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="allowed_emails",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="ユーザー",
                    ),
                ),
            ],
            options={
                "verbose_name": "許可 email",
                "verbose_name_plural": "許可 email",
                "db_table": "m_user_allowed_emails",
                "indexes": [models.Index(fields=["user"], name="m_user_allo_user_id_1ec9e9_idx")],
            },
        ),
        migrations.RunPython(_populate_allowed_emails_from_existing_users, reverse_code=_noop_reverse),
    ]
