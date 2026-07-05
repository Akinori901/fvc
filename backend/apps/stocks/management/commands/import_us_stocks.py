"""米国株一括登録コマンド。yfinance から銘柄情報を取得して m_stocks に登録する。"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "yfinance を使って米国株をまとめて登録する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--codes",
            required=True,
            help="カンマ区切りのティッカーコード（例: AAPL,MSFT,GOOGL）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="実際のDB書き込みを行わない",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            import yfinance as yf
        except ImportError as e:
            msg = "yfinance がインストールされていません。'pip install yfinance' を実行してください。"
            raise CommandError(msg) from e

        codes = [c.strip().upper() for c in options["codes"].split(",") if c.strip()]
        dry_run = options["dry_run"]

        if not codes:
            raise CommandError("--codes に有効なティッカーコードを指定してください。")

        self.stdout.write(f"対象ティッカー: {', '.join(codes)} (dry_run={dry_run})")

        success = 0
        failed = 0

        for code in codes:
            try:
                ticker = yf.Ticker(code)
                info = ticker.info
                name = info.get("longName") or info.get("shortName") or code
                sector = info.get("sector") or ""

                if dry_run:
                    self.stdout.write(f"  [DRY RUN] {code}: name={name}, sector={sector}")
                    success += 1
                    continue

                from apps.stocks.models import Stock

                _, created = Stock.objects.update_or_create(
                    code=code,
                    defaults={
                        "name": name,
                        "market": "US",
                        "market_type": "US",
                        "sector": sector,
                        "is_active": True,
                    },
                )
                action = "作成" if created else "更新"
                self.stdout.write(self.style.SUCCESS(f"  {code}: {name} ({sector}) [{action}]"))
                success += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  {code}: エラー — {e}"))
                failed += 1

        self.stdout.write(f"\n完了: 成功 {success} 件 / 失敗 {failed} 件")
        if not dry_run and success > 0:
            self.stdout.write("財務・株価データを取得するには以下を実行してください:")
            self.stdout.write("  python manage.py sync_financials --market US")
            self.stdout.write("  python manage.py sync_prices --market US")
