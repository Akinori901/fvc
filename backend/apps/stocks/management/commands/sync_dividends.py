"""配当・分配金同期コマンド。"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "外部APIから配当・分配金データを同期する"

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
            "--instrument-type",
            choices=["stock", "etf", "reit"],
            default=None,
            help="対象種別 (未指定時はETF+REITのみ)",
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
        instrument_type = options["instrument_type"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                f"[DRY RUN] 配当・分配金同期 (market={market}, codes={codes}, instrument_type={instrument_type})"
            )
            return

        label = instrument_type or "ETF+REIT"
        self.stdout.write(f"配当・分配金同期を開始します (market={market}, type={label})...")

        usecase = sync_market_data_usecase()
        log = usecase.sync_dividends(market_type=market, codes=codes, instrument_type=instrument_type)

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: status={log.status}, "
                f"total={log.total_count}, "
                f"success={log.success_count}, "
                f"errors={log.error_count}"
            )
        )
