"""日本株おすすめ抽出APIビュー。

スナップショット方式: t_recommendation_snapshots を SELECT するだけ。
重い計算は Worker Lambda 上で generate_recommendations コマンドが定期実行する。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request  # noqa: TC002
from rest_framework.response import Response
from rest_framework.views import APIView

# JST タイムゾーン
_JST = timezone(timedelta(hours=9))


class RecommendationsView(APIView):
    """GET /api/stocks/recommendations/ — 日本株3カテゴリのおすすめ各5件"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.stocks.models import RecommendationSnapshot

        snapshots = list(RecommendationSnapshot.objects.select_related("stock").order_by("category", "rank"))

        result: dict[str, list[dict[str, object]]] = {
            "long_term": [],
            "day_trade": [],
            "range_bound": [],
        }
        latest_generated: datetime | None = None

        for s in snapshots:
            result.setdefault(s.category, []).append(
                {
                    "code": s.stock.code,
                    "name": s.stock.name,
                    "latest_price": str(s.latest_price) if s.latest_price is not None else None,
                    "metrics": s.metrics,
                }
            )
            if latest_generated is None or s.generated_at > latest_generated:
                latest_generated = s.generated_at

        return Response(
            {
                "generated_at": (
                    latest_generated.astimezone(_JST).isoformat()
                    if latest_generated is not None
                    else datetime.now(_JST).isoformat()
                ),
                "long_term": result["long_term"],
                "day_trade": result["day_trade"],
                "range_bound": result["range_bound"],
            }
        )
