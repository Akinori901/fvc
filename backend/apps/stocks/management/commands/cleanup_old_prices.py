"""古い株価データを削除するコマンド。

Usage:
    python manage.py cleanup_old_prices              # 2年以上前を削除
    python manage.py cleanup_old_prices --keep-days 365  # 1年以上前を削除
    python manage.py cleanup_old_prices --dry-run    # 削除対象件数のみ表示
"""

from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.stocks.models import StockPrice


class Command(BaseCommand):
    help = "指定日数より古い株価データを削除する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--keep-days",
            type=int,
            default=730,
            help="保持する日数（デフォルト: 730日 = 約2年）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除せず、対象件数のみ表示",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        keep_days = options["keep_days"]
        dry_run = options["dry_run"]
        cutoff_date = date.today() - timedelta(days=keep_days)

        queryset = StockPrice.objects.filter(date__lt=cutoff_date)
        count = queryset.count()

        if dry_run:
            self.stdout.write(f"[dry-run] {cutoff_date} より前の株価データ: {count:,} 件（削除されません）")
            return

        if count == 0:
            self.stdout.write("削除対象のデータはありません")
            return

        deleted, _ = queryset.delete()
        self.stdout.write(self.style.SUCCESS(f"{cutoff_date} より前の株価データ {deleted:,} 件を削除しました"))
