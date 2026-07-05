"""信用取引残高データ同期コマンド。

Usage:
    # JP市場の全銘柄（直近90日）
    manage.py sync_margin

    # 特定銘柄
    manage.py sync_margin --code 5892 --code 8729

    # 直近N日分
    manage.py sync_margin --days 180

    # 開始日を指定
    manage.py sync_margin --from-date 2025-01-01
"""

from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "J-Quantsから信用取引残高データを同期する"

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
            help="対象銘柄コード（複数指定可）",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="取得開始日 (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="直近N日分を取得 (デフォルト: 90)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.application.services.margin_sync_service import MarginSyncService
        from config.container import jquants_provider, margin_repository, stock_repository

        market = options["market"]
        codes = options["codes"]
        days = options["days"]

        from_date: date | None = None
        if options["from_date"]:
            try:
                from_date = date.fromisoformat(options["from_date"])
            except ValueError:
                self.stdout.write(self.style.ERROR("--from-date の形式が不正です (YYYY-MM-DD)"))
                return
        else:
            from_date = date.today() - timedelta(days=days)

        self.stdout.write(f"信用残高同期を開始します (market={market}, codes={codes or '全銘柄'}, from={from_date})...")

        provider = jquants_provider(market)
        service = MarginSyncService(
            stock_repo=stock_repository(),
            margin_repo=margin_repository(),
        )
        total, saved, errors = service.sync(
            provider=provider,
            market_type=market,
            codes=codes,
            from_date=from_date,
        )

        self.stdout.write(self.style.SUCCESS(f"完了: 対象={total}銘柄, 保存={saved}件, エラー={len(errors)}件"))
        for err in errors[:5]:
            self.stdout.write(self.style.WARNING(f"  エラー: {err}"))
        if len(errors) > 5:
            self.stdout.write(self.style.WARNING(f"  ... 他 {len(errors) - 5} 件"))
