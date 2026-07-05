"""日次急騰急落集計コマンド。

EventBridge から平日 18:00 JST に実行され、当日の前日比・出来高比・UL/LL を
`t_daily_movers` に再生成する。

使い方:
    python manage.py compute_movers                  # 各銘柄の最新営業日を集計
    python manage.py compute_movers --date 2026-05-15  # 指定日を集計
"""

from __future__ import annotations

import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "全アクティブ JP 銘柄の前日比・出来高比・UL/LL を t_daily_movers に再計算する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="集計対象日 (YYYY-MM-DD)。省略時は各銘柄の最新営業日を使用",
        )
        parser.add_argument(
            "--market",
            choices=["JP", "US"],
            default="JP",
            help="対象市場 (デフォルト: JP)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import compute_daily_movers_usecase

        target_date: datetime.date | None = None
        if options.get("date"):
            target_date = datetime.date.fromisoformat(options["date"])

        market = options["market"]

        self.stdout.write(f"compute_movers 開始: market={market} target_date={target_date or 'latest'}")
        usecase = compute_daily_movers_usecase()
        result = usecase.execute(target_date=target_date, market_type=market)

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: 集計 {result['computed']} 銘柄 / 保存 {result['saved']} 件 / スキップ {result['skipped']} 件"
            )
        )
