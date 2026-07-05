"""銘柄別ニュース View。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from config import container

from ..serializers import news_entity_to_dict

if TYPE_CHECKING:
    from rest_framework.request import Request


class StockNewsView(APIView):
    """GET /api/news/stocks/<code>/ — 特定銘柄に紐付くニュース一覧"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, code: str) -> Response:
        paginator = StandardPagination()
        page_size = paginator.get_page_size(request) or paginator.page_size
        try:
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        offset = (page_number - 1) * page_size

        usecase = container.list_stock_news_usecase()
        try:
            entities, total = usecase.execute(code=code, limit=page_size, offset=offset)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": [news_entity_to_dict(e) for e in entities],
            }
        )
