"""link_fund_proxies の逆操作。投信保有から proxy_stock_id を全て NULL に戻す。

緊急ロールバック用途 (2026-05-27 の link_fund_proxies 反映で MTD 計算が暴走したため)。
proxy 計算のバグ修正 (views.py _calc_stock_total の JPY 化 + 比率ガード) が
本番反映された後で、改めて link_fund_proxies を実行する想定。
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.portfolios.models import AccountHolding


class Command(BaseCommand):
    help = "投資信託保有の proxy_stock_id を NULL に戻す (link_fund_proxies の逆操作)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="実際には更新しない")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        targets = AccountHolding.objects.filter(
            asset_type="fund",
            proxy_stock_id__isnull=False,
        )
        count = targets.count()

        if count == 0:
            self.stdout.write("対象レコードなし (proxy_stock_id 未設定の投信保有のみ)")
            return

        # サンプル表示 (先頭 10 件)
        sample = list(targets.values("id", "asset_name", "proxy_stock_id")[:10])
        action = "DRY" if dry_run else "UNLINK"
        self.stdout.write(f"対象: {count} 件 (asset_type='fund' かつ proxy_stock_id IS NOT NULL)")
        self.stdout.write("--- サンプル (先頭 10 件) ---")
        for h in sample:
            self.stdout.write(
                f"  [{action}] holding_id={h['id']} {h['asset_name'][:50]:50} proxy={h['proxy_stock_id']}"
            )
        if count > len(sample):
            self.stdout.write(f"  ... 他 {count - len(sample)} 件")

        if not dry_run:
            updated = targets.update(proxy_stock_id=None)
            self.stdout.write(f"\n完了: {updated} 件 unlink")
        else:
            self.stdout.write(f"\n[DRY RUN] 完了: {count} 件 unlink 予定")
