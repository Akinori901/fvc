"""デフォルトモデルを gemini-2.5-flash に更新。

gemini-2.0-flash の無料枠が廃止(limit:0)されたため。
既存レコードも gemini-2.5-flash に移行する。
"""

from django.db import migrations, models


def migrate_model_name(apps: object, schema_editor: object) -> None:
    UserAiConfig = apps.get_model("ai", "UserAiConfig")  # type: ignore[attr-defined]
    UserAiConfig.objects.filter(model="gemini-2.0-flash").update(model="gemini-2.5-flash")


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0002_change_default_to_gemini"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraiconfig",
            name="model",
            field=models.CharField(
                "使用モデル",
                max_length=100,
                default="gemini-2.5-flash",
            ),
        ),
        migrations.RunPython(migrate_model_name, migrations.RunPython.noop),
    ]
