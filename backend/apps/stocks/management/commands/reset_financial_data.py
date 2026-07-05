"""財務データリセットコマンド。

再上場・コード再利用時に旧会社の財務データを削除して、
J-Quants から新たに取得し直す。

Usage:
    # 財務データを削除して即時再取得
    manage.py reset_financial_data --code 8729

    # 削除のみ（再取得しない）
    manage.py reset_financial_data --code 8729 --no-resync

    # 手動入力データも削除
    manage.py reset_financial_data --code 8729 --clear-manual

    # 削除件数確認のみ
    manage.py reset_financial_data --code 8729 --dry-run
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "銘柄の財務データをリセットし、J-Quantsから再取得する（再上場・コード再利用時に使用）"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            required=True,
            help="対象銘柄コード（複数指定可）",
        )
        parser.add_argument(
            "--no-resync",
            action="store_true",
            help="削除後に J-Quants から再取得しない",
        )
        parser.add_argument(
            "--clear-manual",
            action="store_true",
            help="手動入力財務データ（t_financial_manual_inputs）も削除する",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除せず対象件数のみ表示",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import FinancialManualInput, Stock, StockFinancial

        codes = options["codes"]
        no_resync = options["no_resync"]
        clear_manual = options["clear_manual"]
        dry_run = options["dry_run"]

        stocks = list(Stock.objects.filter(code__in=codes))
        if not stocks:
            self.stdout.write(self.style.WARNING("対象銘柄が見つかりません"))
            return

        for stock in stocks:
            auto_count = StockFinancial.objects.filter(stock=stock).count()
            manual_count = FinancialManualInput.objects.filter(stock=stock).count()

            self.stdout.write(
                f"{stock.code} {stock.name}: 自動財務データ={auto_count}件, 手動財務データ={manual_count}件"
            )

            if dry_run:
                self.stdout.write(f"  [dry-run] 自動財務データ {auto_count}件を削除予定")
                if clear_manual:
                    self.stdout.write(f"  [dry-run] 手動財務データ {manual_count}件を削除予定")
                continue

            # 自動取得財務データを削除
            deleted_auto, _ = StockFinancial.objects.filter(stock=stock).delete()
            self.stdout.write(self.style.SUCCESS(f"  自動財務データ {deleted_auto}件削除"))

            # 手動入力データも削除する場合
            if clear_manual:
                deleted_manual, _ = FinancialManualInput.objects.filter(stock=stock).delete()
                self.stdout.write(self.style.SUCCESS(f"  手動財務データ {deleted_manual}件削除"))

            # J-Quants から再取得
            if not no_resync:
                self.stdout.write("  J-Quants から財務データを再取得中...")
                try:
                    from config.container import sync_market_data_usecase

                    usecase = sync_market_data_usecase()
                    log = usecase.sync_financials(
                        market_type=stock.market_type,
                        codes=[stock.code],
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"  再取得完了: {log.success_count}件取得 (errors={log.error_count})")
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  再取得失敗: {e}"))
