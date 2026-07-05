import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("stocks", "0001_initial"),
        ("portfolios", "0007_portfolioaccount_expected_return_rate"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountholding",
            name="proxy_stock",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="proxy_holdings",
                to="stocks.stock",
                verbose_name="プロキシETF",
            ),
        ),
    ]
