"""EDINET大株主データ同期コマンド。"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "EDINET有価証券報告書から大株主データを同期し、オーナー経営判定を行う"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--from-date",
            type=str,
            default=None,
            help="開始日 (YYYY-MM-DD)。未指定時は直近30日",
        )
        parser.add_argument(
            "--to-date",
            type=str,
            default=None,
            help="終了日 (YYYY-MM-DD)。未指定時は今日",
        )
        parser.add_argument(
            "--code",
            action="append",
            dest="codes",
            help="対象銘柄コード (複数指定可)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB書き込みを行わない",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import sync_shareholders_usecase

        to_date = options["to_date"] or date.today().isoformat()
        from_date = options["from_date"] or (date.today() - timedelta(days=30)).isoformat()
        codes = options["codes"]
        dry_run = options["dry_run"]

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"{prefix}大株主データ同期を開始します (from={from_date}, to={to_date}, codes={codes})")

        usecase = sync_shareholders_usecase()
        stats = usecase.execute(
            from_date=from_date,
            to_date=to_date,
            codes=codes,
            dry_run=dry_run,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: processed={stats['processed']}, "
                f"matched={stats['matched']}, "
                f"skipped={stats['skipped']}, "
                f"errors={stats['errors']}"
            )
        )
