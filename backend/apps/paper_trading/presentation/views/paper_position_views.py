"""仮想売買ポジションビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.paper_trading.application.dto import PositionDTO


class PaperPositionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.list_positions_usecase()
        result = usecase.execute(request.user.id)

        return Response(
            {
                "positions": [_position_to_dict(p) for p in result.positions],
                "summary": {
                    "total_investment": str(result.total_investment),
                    "total_unrealized_profit": str(result.total_unrealized_profit),
                    "total_realized_profit": str(result.total_realized_profit),
                    "position_count": result.position_count,
                },
            }
        )


class PaperPositionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, code: str) -> Response:
        assert isinstance(request.user.id, int)

        stock_repo = container.stock_repository()
        stock = stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            return Response(
                {"detail": f"銘柄 {code} が見つかりません。"},
                status=status.HTTP_404_NOT_FOUND,
            )

        position_repo = container.paper_position_repository()
        pos = position_repo.find_by_user_and_stock(request.user.id, stock.id)

        if pos is None or pos.quantity == 0:
            return Response(None)

        from decimal import ROUND_HALF_UP, Decimal

        unrealized: Decimal | None = None
        unrealized_pct: Decimal | None = None
        if stock.latest_price is not None and pos.avg_cost_price > 0:
            unrealized = (stock.latest_price - pos.avg_cost_price) * pos.quantity
            unrealized_pct = ((stock.latest_price - pos.avg_cost_price) / pos.avg_cost_price * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        return Response(
            {
                "stock_code": stock.code,
                "stock_name": stock.name,
                "quantity": pos.quantity,
                "avg_cost_price": str(pos.avg_cost_price),
                "total_cost": str(pos.total_cost),
                "latest_price": str(stock.latest_price) if stock.latest_price else None,
                "unrealized_profit": str(unrealized) if unrealized is not None else None,
                "unrealized_profit_pct": str(unrealized_pct) if unrealized_pct is not None else None,
                "realized_profit_total": str(pos.realized_profit_total),
            }
        )


def _position_to_dict(p: PositionDTO) -> dict[str, object]:
    return {
        "stock_code": p.stock_code,
        "stock_name": p.stock_name,
        "quantity": p.quantity,
        "avg_cost_price": str(p.avg_cost_price),
        "total_cost": str(p.total_cost),
        "latest_price": str(p.latest_price) if p.latest_price is not None else None,
        "unrealized_profit": str(p.unrealized_profit) if p.unrealized_profit is not None else None,
        "unrealized_profit_pct": str(p.unrealized_profit_pct) if p.unrealized_profit_pct is not None else None,
        "realized_profit_total": str(p.realized_profit_total),
    }
