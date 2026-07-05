"""仮想売買リセットビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class PaperTradingResetView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.reset_paper_trading_usecase()
        deleted_trades, deleted_positions = usecase.execute(request.user.id)

        return Response(
            {
                "deleted_trades": deleted_trades,
                "deleted_positions": deleted_positions,
            }
        )
