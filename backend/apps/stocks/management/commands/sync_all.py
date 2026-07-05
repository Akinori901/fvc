"""全データ同期コマンド。"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "外部APIから全データ（銘柄・財務・株価）を同期する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--market",
            choices=["JP", "US"],
            default="JP",
            help="対象市場 (デフォルト: JP)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="実際のDB書き込みを行わない",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import sync_market_data_usecase

        market = options["market"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(f"[DRY RUN] 全データ同期 (market={market})")
            return

        self.stdout.write(f"全データ同期を開始します (market={market})...")
        self.stdout.write("=" * 50)

        usecase = sync_market_data_usecase()
        logs = usecase.sync_all(market_type=market)

        self.stdout.write("=" * 50)
        for log in logs:
            self.stdout.write(
                f"  [{log.sync_type}] status={log.status}, "
                f"total={log.total_count}, "
                f"success={log.success_count}, "
                f"errors={log.error_count}"
            )

        self.stdout.write(self.style.SUCCESS("全データ同期が完了しました"))
