"""同期APIビュー。"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

if TYPE_CHECKING:
    from rest_framework.request import Request

    from apps.stocks.domain.entities import SyncLogEntity


class SyncTriggerView(APIView):
    """POST /api/stocks/sync/ — 同期をトリガー。"""

    def post(self, request: Request) -> Response:
        from config.container import sync_market_data_usecase

        sync_type = request.data.get("sync_type", "all")
        market_type = request.data.get("market_type", "JP")
        codes = request.data.get("codes")
        fiscal_year = request.data.get("fiscal_year")
        from_date_str = request.data.get("from_date")
        force = request.data.get("force", False)

        from_date = date.fromisoformat(from_date_str) if from_date_str else None

        usecase = sync_market_data_usecase()

        if sync_type == "stocks":
            log = usecase.sync_stocks(market_type=market_type)
            return Response(_log_to_dict(log), status=status.HTTP_200_OK)
        elif sync_type == "financials":
            log = usecase.sync_financials(market_type=market_type, codes=codes, fiscal_year=fiscal_year)
            return Response(_log_to_dict(log), status=status.HTTP_200_OK)
        elif sync_type == "prices":
            log = usecase.sync_prices(market_type=market_type, codes=codes, from_date=from_date, force=force)
            return Response(_log_to_dict(log), status=status.HTTP_200_OK)
        elif sync_type == "dividends":
            log = usecase.sync_dividends(market_type=market_type, codes=codes)
            return Response(_log_to_dict(log), status=status.HTTP_200_OK)
        elif sync_type == "all":
            logs = usecase.sync_all(market_type=market_type)
            return Response([_log_to_dict(log) for log in logs], status=status.HTTP_200_OK)
        else:
            return Response(
                {"detail": f"不正な sync_type: {sync_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SyncLogListView(APIView):
    """GET /api/stocks/sync/logs/ — 同期ログ一覧。"""

    def get(self, request: Request) -> Response:
        from config.container import sync_log_repository

        limit = int(request.query_params.get("limit", 20))
        repo = sync_log_repository()
        logs = repo.list_recent(limit=limit)
        return Response([_log_to_dict(log) for log in logs])


def _log_to_dict(log: SyncLogEntity) -> dict[str, object]:
    return {
        "id": log.id,
        "sync_type": log.sync_type,
        "provider": log.provider,
        "market": log.market,
        "status": log.status,
        "started_at": str(log.started_at) if log.started_at else None,
        "finished_at": str(log.finished_at) if log.finished_at else None,
        "total_count": log.total_count,
        "success_count": log.success_count,
        "error_count": log.error_count,
    }
