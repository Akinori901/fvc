"""投資信託の保有銘柄にプロキシETFを紐づける."""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.portfolios.models import AccountHolding
from apps.stocks.models import Stock

# asset_name の部分一致 → プロキシETFコード（先頭から優先マッチ）
FUND_PROXY_MAP: list[tuple[str, str]] = [
    ("S&P500", "1557"),
    ("Ｓ＆Ｐ５００", "1557"),
    ("米国株式", "1557"),
    ("米国成長株", "1557"),
    ("全米株式", "VTI"),
    ("VTI", "VTI"),
    ("オールカントリー", "ACWI"),
    ("オール・カントリー", "ACWI"),
    ("全世界株式", "ACWI"),
    ("FANG+", "QQQ"),
    ("ＦＡＮＧ", "QQQ"),
    ("NASDAQ", "1545"),
    ("ＮＡＳＤＡＱ", "1545"),
    ("日経225", "1321"),
    ("日経平均", "1321"),
    ("日本株", "1321"),
    ("国内株", "1321"),
    ("TOPIX", "1321"),
    ("中小型", "1321"),
    ("先進国株式", "1550"),
    ("インド", "1678"),
    ("ゴールド", "GLD"),
    ("Gold", "GLD"),
    ("おおぶね", "1557"),
]


class Command(BaseCommand):
    help = "投資信託の保有銘柄にプロキシETF(proxy_stock)を紐づける"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="実際には更新しない")

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]

        targets = AccountHolding.objects.filter(
            asset_type="fund",
            proxy_stock_id__isnull=True,
        )

        if not targets.exists():
            self.stdout.write("対象レコードなし（全て proxy_stock 設定済み）")
            return

        # プロキシETFコード → Stock.pk マップ
        proxy_codes = {code for _, code in FUND_PROXY_MAP}
        code_to_pk: dict[str, int] = {}
        for s in Stock.objects.filter(code__in=proxy_codes).only("id", "code"):
            code_to_pk[s.code] = s.pk

        linked = 0
        skipped = 0
        for holding in targets:
            matched_code: str | None = None
            for keyword, code in FUND_PROXY_MAP:
                if keyword in holding.asset_name:
                    matched_code = code
                    break

            if matched_code and matched_code in code_to_pk:
                proxy_pk = code_to_pk[matched_code]
                action = "DRY" if dry_run else "SET"
                self.stdout.write(f"  [{action}] {holding.asset_name[:40]} → {matched_code} (pk={proxy_pk})")
                if not dry_run:
                    holding.proxy_stock_id = proxy_pk
                    holding.save(update_fields=["proxy_stock_id"])
                linked += 1
            else:
                self.stdout.write(f"  [SKIP] {holding.asset_name[:40]} (マッチなし)")
                skipped += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(f"\n{prefix}完了: {linked}件 紐づけ, {skipped}件 スキップ")
