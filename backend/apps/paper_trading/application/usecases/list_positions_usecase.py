"""ポジション一覧取得ユースケース。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from apps.paper_trading.application.dto import PositionDTO, PositionListDTO

if TYPE_CHECKING:
    from apps.paper_trading.domain.repositories import PaperPositionRepository
    from apps.stocks.domain.repositories import StockRepository


class ListPositionsUseCase:
    def __init__(
        self,
        position_repo: PaperPositionRepository,
        stock_repo: StockRepository,
    ) -> None:
        self._position_repo = position_repo
        self._stock_repo = stock_repo

    def execute(self, user_id: int) -> PositionListDTO:
        positions = self._position_repo.find_all_by_user(user_id)

        # stock_id → StockEntity のマッピング
        stock_ids = [p.stock_id for p in positions]
        stocks_map = {}
        for sid in stock_ids:
            s = self._stock_repo.find_by_id(sid)
            if s:
                stocks_map[sid] = s

        result: list[PositionDTO] = []
        total_investment = Decimal("0")
        total_unrealized = Decimal("0")
        total_realized = Decimal("0")

        for pos in positions:
            stock = stocks_map.get(pos.stock_id)
            stock_code = stock.code if stock else str(pos.stock_id)
            stock_name = stock.name if stock else "不明"
            latest_price = stock.latest_price if stock else None

            unrealized: Decimal | None = None
            unrealized_pct: Decimal | None = None
            if latest_price is not None and pos.avg_cost_price > 0:
                unrealized = (latest_price - pos.avg_cost_price) * pos.quantity
                unrealized_pct = ((latest_price - pos.avg_cost_price) / pos.avg_cost_price * Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            result.append(
                PositionDTO(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=pos.quantity,
                    avg_cost_price=pos.avg_cost_price,
                    total_cost=pos.total_cost,
                    latest_price=latest_price,
                    unrealized_profit=unrealized,
                    unrealized_profit_pct=unrealized_pct,
                    realized_profit_total=pos.realized_profit_total,
                )
            )

            total_investment += pos.total_cost
            if unrealized is not None:
                total_unrealized += unrealized
            total_realized += pos.realized_profit_total

        return PositionListDTO(
            positions=result,
            total_investment=total_investment,
            total_unrealized_profit=total_unrealized,
            total_realized_profit=total_realized,
            position_count=len(result),
        )
