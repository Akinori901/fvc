"""上場廃止銘柄の誤った株価データを削除するコマンド。

Usage:
    # is_active=False の銘柄を全件修正
    python manage.py fix_delisted_prices

    # 特定銘柄を指定（is_active に関わらず対象）
    python manage.py fix_delisted_prices --code 8729

    # 削除対象を確認するだけ（DBは変更しない）
    python manage.py fix_delisted_prices --code 8729 --dry-run
"""

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "上場廃止銘柄の誤った株価データを削除し latest_price をリセットする"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            help="対象銘柄コード（複数指定可）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除せず対象件数のみ表示",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import Stock, StockFinancial, StockPrice

        codes = options["codes"]
        dry_run = options["dry_run"]

        stocks = list(Stock.objects.filter(code__in=codes)) if codes else list(Stock.objects.filter(is_active=False))

        if not stocks:
            self.stdout.write("対象銘柄なし")
            return

        for stock in stocks:
            latest_fin = StockFinancial.objects.filter(stock=stock).order_by("-fiscal_year").first()
            if not latest_fin:
                self.stdout.write(f"  {stock.code} {stock.name}: 財務データなし → スキップ")
                continue

            cutoff = date(latest_fin.fiscal_year + 2, 12, 31)
            qs = StockPrice.objects.filter(stock=stock, date__gt=cutoff)
            count = qs.count()

            if count == 0:
                self.stdout.write(f"  {stock.code} {stock.name}: 削除対象なし")
                continue

            if dry_run:
                self.stdout.write(f"  [dry-run] {stock.code} {stock.name}: {count}件が削除対象 (cutoff={cutoff})")
                continue

            qs.delete()

            # m_stocks.latest_price をリセット
            latest_price = StockPrice.objects.filter(stock=stock).order_by("-date").first()
            stock.latest_price = latest_price.close_price if latest_price else None
            stock.latest_price_date = latest_price.date if latest_price else None
            stock.save(update_fields=["latest_price", "latest_price_date"])

            self.stdout.write(
                self.style.SUCCESS(
                    f"  {stock.code} {stock.name}: {count}件削除, "
                    f"latest_price={stock.latest_price} ({stock.latest_price_date})"
                )
            )
