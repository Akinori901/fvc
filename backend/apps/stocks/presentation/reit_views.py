"""REIT一覧APIビュー。"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config.container import reit_screening_usecase


class ReitListView(APIView):
    """GET /api/stocks/reit/ — REIT一覧（分配金利回り降順）"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        market_type = request.query_params.get("market_type", "JP")

        usecase = reit_screening_usecase()
        results = usecase.execute(market_type=market_type)

        data = [
            {
                "code": r.code,
                "name": r.name,
                "sector": r.sector,
                "latest_price": str(r.latest_price) if r.latest_price is not None else None,
                "latest_price_date": r.latest_price_date,
                "bps": str(r.bps) if r.bps is not None else None,
                "p_nav": str(r.p_nav) if r.p_nav is not None else None,
                "annual_dividend": str(r.annual_dividend) if r.annual_dividend is not None else None,
                "dividend_yield": str(r.dividend_yield) if r.dividend_yield is not None else None,
                "eps": str(r.eps) if r.eps is not None else None,
                "evaluation_zone": r.evaluation_zone,
                "evaluation_score": r.evaluation_score,
                "evaluation_signals": [
                    {"category": s.category, "label": s.label, "impact": s.impact} for s in r.evaluation_signals
                ],
                "price_position_52w": str(r.price_position_52w) if r.price_position_52w is not None else None,
                "payout_coverage": str(r.payout_coverage) if r.payout_coverage is not None else None,
            }
            for r in results
        ]
        return Response(data)
