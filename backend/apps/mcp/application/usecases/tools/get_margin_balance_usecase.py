"""信用残取得ツール UseCase。

t_margin_balances から指定銘柄の最新信用残と直近 4 週分の履歴を返す。
公開情報のため user_id は不要。
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.domain.entities import MarginBalanceEntity
    from apps.stocks.domain.repositories import MarginRepository, StockRepository


_HISTORY_LIMIT = 4


class GetMarginBalanceToolUseCase:
    """銘柄の信用残（買残・売残・信用倍率・直近4週履歴）を返す。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        margin_repo: MarginRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._margin_repo = margin_repo

    def execute(self, *, code: str) -> dict[str, Any]:
        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {code}")

        latest = self._margin_repo.find_latest_by_stock_id(stock.id)
        history = self._margin_repo.find_recent_by_stock_id(stock.id, limit=_HISTORY_LIMIT)

        return {
            "code": stock.code,
            "name": stock.name,
            "as_of": latest.date.isoformat() if latest is not None else None,
            "buy_balance_shares": latest.long_balance if latest else None,
            "sell_balance_shares": latest.short_balance if latest else None,
            "buy_balance_change": latest.long_balance_change if latest else None,
            "sell_balance_change": latest.short_balance_change if latest else None,
            "sl_ratio": _decimal_or_none(latest.sl_ratio) if latest else None,
            "credit_ratio": _credit_ratio(latest) if latest else None,
            "history_last_4w": [
                {
                    "date": entry.date.isoformat(),
                    "buy_balance_shares": entry.long_balance,
                    "sell_balance_shares": entry.short_balance,
                    "buy_balance_change": entry.long_balance_change,
                    "sell_balance_change": entry.short_balance_change,
                    "sl_ratio": _decimal_or_none(entry.sl_ratio),
                }
                for entry in history
            ],
        }


def _credit_ratio(entry: MarginBalanceEntity) -> str | None:
    """信用倍率 = 買残 / 売残 を返す。売残 0 のときは None。"""
    if entry.long_balance is None or entry.short_balance is None or entry.short_balance == 0:
        return None
    return str(Decimal(entry.long_balance) / Decimal(entry.short_balance))


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
