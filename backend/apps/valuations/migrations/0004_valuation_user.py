"""Add user ForeignKey to Valuation model.

Step 1: Add nullable user column
Step 2: Backfill existing rows with user_id=2 (akinori)
Step 3: Make column NOT NULL
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_user(apps, schema_editor):
    """既存レコードを akinori (id=2) に紐づける"""
    Valuation = apps.get_model("valuations", "Valuation")
    Valuation.objects.filter(user__isnull=True).update(user_id=2)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("valuations", "0003_valuation_bps_valuation_cost_of_capital_and_more"),
    ]

    operations = [
        # Step 1: Add nullable
        migrations.AddField(
            model_name="valuation",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="valuations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ユーザー",
            ),
        ),
        # Step 2: Backfill
        migrations.RunPython(backfill_user, migrations.RunPython.noop),
        # Step 3: Make NOT NULL
        migrations.AlterField(
            model_name="valuation",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="valuations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="ユーザー",
            ),
        ),
    ]
