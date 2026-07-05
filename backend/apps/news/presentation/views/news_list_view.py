"""ニュース一覧 View。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from config import container

from ..serializers import NewsListFilterSerializer, news_entity_to_dict

if TYPE_CHECKING:
    from rest_framework.request import Request


class NewsListView(APIView):
    """GET /api/news/ — ニュース一覧（ページネーション・フィルタ付き）"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        filter_serializer = NewsListFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        filters = filter_serializer.validated_data

        paginator = StandardPagination()
        page_size = paginator.get_page_size(request) or paginator.page_size
        try:
            page_number = int(request.query_params.get(paginator.page_query_param, 1))
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        offset = (page_number - 1) * page_size

        usecase = container.list_news_usecase()
        entities, total = usecase.execute(
            category=filters.get("category"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            keyword=filters.get("keyword") or None,
            limit=page_size,
            offset=offset,
        )

        return Response(
            {
                "count": total,
                "page": page_number,
                "page_size": page_size,
                "results": [news_entity_to_dict(e) for e in entities],
            }
        )
