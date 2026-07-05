"""株価同期コマンド（増分同期対応）。"""

from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "外部APIから株価データを同期する（増分同期）"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--market",
            choices=["JP", "US"],
            default="JP",
            help="対象市場 (デフォルト: JP)",
        )
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            help="対象銘柄コード (複数指定可)",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="取得開始日 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--days",
            type=int,
            help="過去N日分を取得",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="増分ではなく全期間を再取得",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="実際のDB書き込みを行わない",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import sync_market_data_usecase

        market = options["market"]
        codes = options["codes"]
        from_date_str = options["from_date"]
        days = options["days"]
        force = options["force"]
        dry_run = options["dry_run"]

        from_date = None
        if from_date_str:
            from_date = date.fromisoformat(from_date_str)
        elif days:
            from_date = date.today() - timedelta(days=days)

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] 株価同期 (market={market}, codes={codes}, from_date={from_date}, force={force})"
            )
            return

        self.stdout.write(f"株価同期を開始します (market={market})...")

        usecase = sync_market_data_usecase()
        log = usecase.sync_prices(
            market_type=market,
            codes=codes,
            from_date=from_date,
            force=force,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: status={log.status}, "
                f"total={log.total_count}, "
                f"success={log.success_count}, "
                f"errors={log.error_count}"
            )
        )
