"""売買履歴取得ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.paper_trading.application.dto import TradeHistoryDTO

if TYPE_CHECKING:
    from apps.paper_trading.domain.repositories import PaperTradeRepository
    from apps.stocks.domain.repositories import StockRepository


class GetTradeHistoryUseCase:
    def __init__(
        self,
        trade_repo: PaperTradeRepository,
        stock_repo: StockRepository,
    ) -> None:
        self._trade_repo = trade_repo
        self._stock_repo = stock_repo

    def execute(self, user_id: int, stock_code: str | None = None) -> list[TradeHistoryDTO]:
        stock_id: int | None = None
        if stock_code:
            stock = self._stock_repo.find_by_code(stock_code)
            if stock and stock.id:
                stock_id = stock.id
            else:
                return []

        trades = self._trade_repo.find_by_user(user_id, stock_id=stock_id)

        # stock_id → stock のマッピング
        stock_ids = {t.stock_id for t in trades}
        stocks_map = {}
        for sid in stock_ids:
            s = self._stock_repo.find_by_id(sid)
            if s:
                stocks_map[sid] = s

        return [
            TradeHistoryDTO(
                id=t.id or 0,
                stock_code=stocks_map[t.stock_id].code if t.stock_id in stocks_map else str(t.stock_id),
                stock_name=stocks_map[t.stock_id].name if t.stock_id in stocks_map else "不明",
                trade_type=t.trade_type,
                quantity=t.quantity,
                price=t.price,
                total_amount=t.total_amount,
                realized_profit=t.realized_profit,
                memo=t.memo,
                traded_at=t.traded_at,  # type: ignore[arg-type]
            )
            for t in trades
        ]
