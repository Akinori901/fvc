"""財務データリセット API ビュー。

再上場・コード再利用時に旧会社の財務データを削除し、
J-Quants から最新データを再取得する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stocks.models import FinancialManualInput, Stock, StockFinancial

if TYPE_CHECKING:
    from rest_framework.request import Request


class FinancialResetView(APIView):
    """POST /api/stocks/{code}/financials/reset/

    リクエストボディ:
        keep_manual (bool): 手動入力データを残すか（デフォルト: true）
        resync (bool): 削除後に J-Quants から再取得するか（デフォルト: true）
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, code: str) -> Response:
        try:
            stock = Stock.objects.get(code=code)
        except Stock.DoesNotExist:
            return Response(
                {"detail": f"銘柄が見つかりません: {code}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        keep_manual: bool = request.data.get("keep_manual", True)
        resync: bool = request.data.get("resync", True)

        # 自動取得財務データを削除
        deleted_auto, _ = StockFinancial.objects.filter(stock=stock).delete()

        # 手動入力データの削除（オプション）
        deleted_manual = 0
        if not keep_manual:
            deleted_manual, _ = FinancialManualInput.objects.filter(stock=stock).delete()

        # J-Quants から再取得
        synced_count = 0
        sync_error: str | None = None
        if resync:
            try:
                from config.container import sync_market_data_usecase

                usecase = sync_market_data_usecase()
                log = usecase.sync_financials(
                    market_type=stock.market_type,
                    codes=[stock.code],
                )
                synced_count = log.success_count
                if log.error_count > 0 and log.error_details:
                    sync_error = str(log.error_details[0])
            except Exception as e:
                sync_error = str(e)

        return Response(
            {
                "deleted_auto": deleted_auto,
                "deleted_manual": deleted_manual,
                "synced_count": synced_count,
                "sync_error": sync_error,
                "message": (
                    f"財務データを{deleted_auto}件削除し、{synced_count}件再取得しました。"
                    if resync
                    else f"財務データを{deleted_auto}件削除しました。"
                ),
            }
        )
