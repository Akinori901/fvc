"""銘柄単位の含み損益取得ツール UseCase。

保有スナップショットの quantity / cost_jpy と StockPriceSource の最新株価を組み合わせ、
holding ごとの市場価値 / 取得原価 / 含み損益を計算する。

day_change_pct は PR3 で daily movers バッチを整備するまで None で返す。
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.portfolios.application.services.dynamic_valuation_service import (
        StockPriceSource,
    )
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        PortfolioAccountRepository,
    )
    from apps.stocks.domain.repositories import StockRepository


class GetMyPnlToolUseCase:
    """銘柄単位の含み損益を返す（要 user_id）。

    code を指定すると該当銘柄のみに絞り込む。
    cost_jpy が NULL の holding は pnl: null として返す（クラッシュさせない）。
    """

    def __init__(
        self,
        account_repo: PortfolioAccountRepository,
        snapshot_repo: AccountSnapshotRepository,
        stock_repo: StockRepository,
        price_source: StockPriceSource,
    ) -> None:
        self._account_repo = account_repo
        self._snapshot_repo = snapshot_repo
        self._stock_repo = stock_repo
        self._price_source = price_source

    def execute(self, *, user_id: int, code: str | None = None) -> dict[str, Any]:
        accounts = self._account_repo.find_by_user(user_id)
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        account_meta_by_id = {a.id: a for a in accounts if a.id is not None}

        target_stock_id: int | None = None
        if code is not None:
            stock = self._stock_repo.find_by_code(code)
            if stock is None or stock.id is None:
                return {"as_of": datetime.date.today().isoformat(), "holdings": []}
            target_stock_id = stock.id

        stock_ids: set[int] = set()
        for snap in snapshots:
            for h in snap.holdings:
                if h.stock_id is None:
                    continue
                if target_stock_id is not None and h.stock_id != target_stock_id:
                    continue
                stock_ids.add(h.stock_id)
        latest_price_map = self._price_source.fetch_latest_prices(stock_ids) if stock_ids else {}

        holdings: list[dict[str, Any]] = []
        for snap in snapshots:
            acc = account_meta_by_id.get(snap.account_id)
            trading_type = acc.trading_type if acc else "spot"
            account_label = (acc.nickname or acc.institution) if acc else ""
            for h in snap.holdings:
                if h.stock_id is None:
                    continue
                if target_stock_id is not None and h.stock_id != target_stock_id:
                    continue

                qty = h.quantity
                cost = h.cost_jpy
                current_price = latest_price_map.get(h.stock_id)
                market_value = qty * current_price if qty is not None and current_price is not None else None
                pnl = (market_value - cost) if market_value is not None and cost is not None else None
                pnl_pct = (pnl / cost * Decimal(100)) if pnl is not None and cost is not None and cost > 0 else None

                holdings.append(
                    {
                        "stock_code": h.ticker_code or None,
                        "stock_id": h.stock_id,
                        "name": h.asset_name,
                        "account_id": snap.account_id,
                        "account_label": account_label,
                        "trading_type": trading_type,
                        "quantity": _decimal_or_none(qty),
                        "avg_cost": _decimal_or_none(h.unit_price),
                        "current_price": _decimal_or_none(current_price),
                        "market_value": _decimal_or_none(market_value),
                        "cost": _decimal_or_none(cost),
                        "unrealized_pnl": _decimal_or_none(pnl),
                        "unrealized_pnl_pct": _decimal_or_none(pnl_pct),
                        "day_change_pct": None,
                    }
                )

        return {
            "as_of": datetime.date.today().isoformat(),
            "holdings": holdings,
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
