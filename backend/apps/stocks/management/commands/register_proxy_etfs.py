"""投資信託の日次変動近似用プロキシETFを m_stocks に登録."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.stocks.models import Stock

_JP = {"market": "ETF", "market_type": "JP", "instrument_type": "etf"}
_US = {"market": "US", "market_type": "US", "instrument_type": "etf"}

PROXY_ETFS = [
    # JP ETFs
    {"code": "1306", "name": "NEXT FUNDS TOPIX連動型上場投信", **_JP},
    {"code": "1557", "name": "SPDR S&P500 ETF", **_JP},
    {"code": "1545", "name": "NEXT FUNDS NASDAQ-100連動型上場投信", **_JP},
    {"code": "1321", "name": "NEXT FUNDS 日経225連動型上場投信", **_JP},
    {"code": "1550", "name": "MAXIS 海外株式(MSCIコクサイ)上場投信", **_JP},
    {"code": "1678", "name": "NEXT FUNDS インド株式指数上場投信", **_JP},
    # US ETFs
    {"code": "VTI", "name": "Vanguard Total Stock Market ETF", **_US},
    {"code": "ACWI", "name": "iShares MSCI ACWI ETF", **_US},
    {"code": "QQQ", "name": "Invesco QQQ Trust", **_US},
    {"code": "GLD", "name": "SPDR Gold Shares", **_US},
]


class Command(BaseCommand):
    help = "投資信託のプロキシETFを m_stocks に登録"

    def handle(self, *args: Any, **options: Any) -> None:
        created = 0
        updated = 0
        for etf in PROXY_ETFS:
            _, is_created = Stock.objects.update_or_create(
                code=etf["code"],
                defaults={
                    "name": etf["name"],
                    "market": etf["market"],
                    "market_type": etf["market_type"],
                    "instrument_type": etf["instrument_type"],
                    "is_active": True,
                },
            )
            status = "作成" if is_created else "更新"
            self.stdout.write(f"  {etf['code']}: {etf['name']} [{status}]")
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(f"\n完了: 作成 {created} 件 / 更新 {updated} 件")
