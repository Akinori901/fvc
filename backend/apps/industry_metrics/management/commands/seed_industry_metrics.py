"""業界指標（東証33業種別の平均ROEレンジ）を投入する管理コマンド。

Usage:
    python manage.py seed_industry_metrics          # 既存レコードはスキップ
    python manage.py seed_industry_metrics --force  # 既存レコードも上書き
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.industry_metrics.models import IndustryMetrics

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "initial_min_roe.json"


class Command(BaseCommand):
    help = "東証33業種の業界平均ROEレンジを投入する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="既存レコードも上書きする",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        force: bool = options["force"]

        if not DATA_FILE.exists():
            self.stderr.write(self.style.ERROR(f"初期データファイルが見つかりません: {DATA_FILE}"))
            return

        with DATA_FILE.open(encoding="utf-8") as f:
            records = json.load(f)

        created = 0
        updated = 0
        skipped = 0

        for rec in records:
            sector = rec["sector"]
            min_roe = Decimal(str(rec["min_roe"]))
            max_roe = Decimal(str(rec["max_roe"]))
            note = rec.get("note", "") or ""

            existing = IndustryMetrics.objects.filter(sector=sector).first()
            if existing is None:
                IndustryMetrics.objects.create(
                    sector=sector,
                    min_roe=min_roe,
                    max_roe=max_roe,
                    note=note,
                )
                created += 1
                self.stdout.write(f"  [created] {sector}: {min_roe} 〜 {max_roe}")
            elif force:
                existing.min_roe = min_roe
                existing.max_roe = max_roe
                existing.note = note
                existing.save()
                updated += 1
                self.stdout.write(f"  [updated] {sector}: {min_roe} 〜 {max_roe}")
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: created={created}, updated={updated}, skipped={skipped} (--force で既存も上書き)"
            )
        )
