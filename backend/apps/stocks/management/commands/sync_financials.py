"""財務データ同期コマンド。"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "外部APIから財務データを同期する"

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
            "--fiscal-year",
            type=int,
            help="対象会計年度",
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
        fiscal_year = options["fiscal_year"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(f"[DRY RUN] 財務データ同期 (market={market}, codes={codes}, fiscal_year={fiscal_year})")
            return

        self.stdout.write(f"財務データ同期を開始します (market={market})...")

        usecase = sync_market_data_usecase()
        log = usecase.sync_financials(
            market_type=market,
            codes=codes,
            fiscal_year=fiscal_year,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: status={log.status}, "
                f"total={log.total_count}, "
                f"success={log.success_count}, "
                f"errors={log.error_count}"
            )
        )
