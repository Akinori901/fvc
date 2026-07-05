"""FXデータ同期コマンド。

USD/JPY レート + 金利データ + PPP を外部 API から同期する。
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "FRED API / yfinance から FX 関連データを同期する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--full",
            action="store_true",
            help="全期間データを再取得する（デフォルトは差分同期）",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import sync_fx_data_usecase

        full = options["full"]
        self.stdout.write(f"FXデータ同期を開始します (full={full})...")

        usecase = sync_fx_data_usecase()
        result = usecase.execute(full=full)

        for key, count in result.items():
            self.stdout.write(f"  {key}: {count}")
        self.stdout.write(self.style.SUCCESS("FXデータ同期が完了しました"))
