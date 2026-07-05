"""信用取引残高 API ビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stocks.models import Stock
from config.container import margin_repository

if TYPE_CHECKING:
    from rest_framework.request import Request


class StockMarginView(APIView):
    """GET /api/stocks/{code}/margin/  — 銘柄別信用残高（最新＋履歴）"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, code: str) -> Response:
        try:
            stock = Stock.objects.get(code=code)
        except Stock.DoesNotExist:
            return Response(
                {"detail": f"銘柄が見つかりません: {code}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        repo = margin_repository()
        history = repo.find_recent_by_stock_id(stock.pk, limit=16)

        def _s(v: object) -> str | None:
            return str(v) if v is not None else None

        history_data = [
            {
                "date": str(e.date),
                "long_balance": e.long_balance,
                "long_balance_change": e.long_balance_change,
                "short_balance": e.short_balance,
                "short_balance_change": e.short_balance_change,
                "sl_ratio": _s(e.sl_ratio),
            }
            for e in history
        ]

        latest = history_data[0] if history_data else None
        return Response({"latest": latest, "history": history_data})
