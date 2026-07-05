"""既存 AccountHolding の ticker_code を m_stocks と照合し、stock_id を設定する。"""

from django.core.management.base import BaseCommand

from apps.portfolios.models import AccountHolding
from apps.stocks.models import Stock


class Command(BaseCommand):
    help = "AccountHolding の ticker_code を m_stocks.code と照合し、stock_id を自動設定する"

    def handle(self, *args: object, **options: object) -> None:
        # stock_id が未設定 & ticker_code があるレコードを取得
        targets = (
            AccountHolding.objects.filter(
                stock_id__isnull=True,
            )
            .exclude(ticker_code__isnull=True)
            .exclude(ticker_code="")
        )

        if not targets.exists():
            self.stdout.write("対象レコードなし（全て stock_id 設定済み）")
            return

        # ticker_code → Stock.pk のマップを構築
        ticker_codes = set(targets.values_list("ticker_code", flat=True))
        stock_map: dict[str, int] = {}
        for s in Stock.objects.filter(code__in=ticker_codes).only("id", "code"):
            stock_map[s.code] = s.pk

        updated = 0
        skipped = 0
        for holding in targets:
            stock_pk = stock_map.get(holding.ticker_code)
            if stock_pk is not None:
                holding.stock_id = stock_pk
                holding.save(update_fields=["stock_id"])
                updated += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(f"完了: {updated}件 stock_id 設定, {skipped}件 m_stocks に該当なし（投資信託等）")
        )
