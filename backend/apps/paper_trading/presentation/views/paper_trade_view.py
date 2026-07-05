"""仮想売買実行・履歴ビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.paper_trading.application.dto import ExecuteTradeDTO
from apps.paper_trading.domain.exceptions import (
    InsufficientPositionError,
    InvalidTradeQuantityError,
    StockPriceUnavailableError,
)
from apps.paper_trading.presentation.serializers import ExecuteTradeSerializer
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class PaperTradeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ExecuteTradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert isinstance(request.user.id, int)
        dto = ExecuteTradeDTO(
            user_id=request.user.id,
            stock_code=serializer.validated_data["stock_code"],
            trade_type=serializer.validated_data["trade_type"],
            quantity=serializer.validated_data["quantity"],
            memo=serializer.validated_data.get("memo", ""),
        )

        usecase = container.execute_trade_usecase()
        try:
            result = usecase.execute(dto)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except (
            InsufficientPositionError,
            InvalidTradeQuantityError,
            StockPriceUnavailableError,
        ) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_trade_result_to_dict(result), status=status.HTTP_201_CREATED)

    def get(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        stock_code = request.query_params.get("stock_code")

        usecase = container.get_trade_history_usecase()
        trades = usecase.execute(request.user.id, stock_code=stock_code)

        return Response([_trade_history_to_dict(t) for t in trades])


def _trade_result_to_dict(r: object) -> dict[str, object]:
    from apps.paper_trading.application.dto import TradeResultDTO

    assert isinstance(r, TradeResultDTO)
    return {
        "trade_id": r.trade_id,
        "trade_type": r.trade_type,
        "stock_code": r.stock_code,
        "stock_name": r.stock_name,
        "quantity": r.quantity,
        "price": str(r.price),
        "total_amount": str(r.total_amount),
        "realized_profit": str(r.realized_profit) if r.realized_profit is not None else None,
        "avg_cost_price": str(r.avg_cost_price),
        "position_quantity": r.position_quantity,
        "position_total_cost": str(r.position_total_cost),
    }


def _trade_history_to_dict(t: object) -> dict[str, object]:
    from apps.paper_trading.application.dto import TradeHistoryDTO

    assert isinstance(t, TradeHistoryDTO)
    return {
        "id": t.id,
        "stock_code": t.stock_code,
        "stock_name": t.stock_name,
        "trade_type": t.trade_type,
        "quantity": t.quantity,
        "price": str(t.price),
        "total_amount": str(t.total_amount),
        "realized_profit": str(t.realized_profit) if t.realized_profit is not None else None,
        "memo": t.memo,
        "traded_at": t.traded_at.isoformat() if t.traded_at else None,
    }
