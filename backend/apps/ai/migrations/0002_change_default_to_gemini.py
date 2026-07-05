# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="useraiconfig",
            name="provider",
            field=models.CharField(
                choices=[("gemini", "Google Gemini"), ("openai", "OpenAI")],
                default="gemini",
                max_length=50,
                verbose_name="プロバイダー",
            ),
        ),
        migrations.AlterField(
            model_name="useraiconfig",
            name="model",
            field=models.CharField(
                default="gemini-2.0-flash",
                max_length=100,
                verbose_name="使用モデル",
            ),
        ),
    ]
