from decimal import Decimal, InvalidOperation
from typing import Any, cast

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolios.models import PortfolioAccount


class PortfolioSimulationView(APIView):
    """GET /api/family-portfolio/simulation/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        years = min(max(int(request.query_params.get("years", "10")), 1), 30)
        view = request.query_params.get("view", "family")
        try:
            fund_rate_pct = Decimal(request.query_params.get("fund_growth_rate", "3"))
        except InvalidOperation:
            fund_rate_pct = Decimal("3")

        from config import container

        usecase = container.portfolio_simulation_usecase()
        result = usecase.execute(
            user_id=cast("int", request.user.pk),
            years=years,
            view=view,
            fund_growth_rate=fund_rate_pct / Decimal("100"),
        )

        ac_labels = dict(PortfolioAccount.AssetClass.choices)

        holdings_data: list[dict[str, Any]] = []
        for h in result.holdings:
            pct = h.growth_rate * Decimal("100")
            holdings_data.append(
                {
                    "asset_name": h.asset_name,
                    "ticker_code": h.ticker_code,
                    "asset_type": h.asset_type,
                    "category": h.category,
                    "category_label": ac_labels.get(h.category, h.category),
                    "current_value": str(h.current_value),
                    "growth_rate": str(h.growth_rate),
                    "growth_rate_percent": str(pct.quantize(Decimal("0.01"))),
                    "growth_rate_source": h.growth_rate_source,
                    "projected_value": str(h.yearly_values[-1]) if h.yearly_values else str(h.current_value),
                    "yearly_values": [str(v) for v in h.yearly_values],
                }
            )

        yearly_by_cat: dict[str, dict[str, Any]] = {}
        for cat, values in result.yearly_by_category.items():
            yearly_by_cat[cat] = {
                "label": ac_labels.get(cat, cat),
                "values": [str(v) for v in values],
            }

        return Response(
            {
                "years": result.years,
                "holdings": holdings_data,
                "yearly_totals": [str(v) for v in result.yearly_totals],
                "yearly_by_category": yearly_by_cat,
            }
        )
