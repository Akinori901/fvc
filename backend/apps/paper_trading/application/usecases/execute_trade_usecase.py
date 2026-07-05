"""売買実行ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.paper_trading.application.dto import ExecuteTradeDTO, TradeResultDTO
from apps.paper_trading.domain.exceptions import StockPriceUnavailableError

if TYPE_CHECKING:
    from apps.paper_trading.application.services.paper_trading_service import (
        PaperTradingService,
    )
    from apps.stocks.domain.repositories import StockRepository


class ExecuteTradeUseCase:
    def __init__(
        self,
        trading_service: PaperTradingService,
        stock_repo: StockRepository,
    ) -> None:
        self._trading_service = trading_service
        self._stock_repo = stock_repo

    @transaction.atomic
    def execute(self, dto: ExecuteTradeDTO) -> TradeResultDTO:
        stock = self._stock_repo.find_by_code(dto.stock_code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄 {dto.stock_code} が見つかりません。")

        if stock.latest_price is None:
            raise StockPriceUnavailableError("株価データがないため売買できません。")

        price = stock.latest_price

        if dto.trade_type == "buy":
            trade, position = self._trading_service.execute_buy(
                user_id=dto.user_id,
                stock_id=stock.id,
                quantity=dto.quantity,
                price=price,
                memo=dto.memo,
            )
        else:
            trade, position = self._trading_service.execute_sell(
                user_id=dto.user_id,
                stock_id=stock.id,
                quantity=dto.quantity,
                price=price,
                memo=dto.memo,
            )

        return TradeResultDTO(
            trade_id=trade.id or 0,
            trade_type=trade.trade_type,
            stock_code=stock.code,
            stock_name=stock.name,
            quantity=trade.quantity,
            price=trade.price,
            total_amount=trade.total_amount,
            realized_profit=trade.realized_profit,
            avg_cost_price=position.avg_cost_price,
            position_quantity=position.quantity,
            position_total_cost=position.total_cost,
        )
