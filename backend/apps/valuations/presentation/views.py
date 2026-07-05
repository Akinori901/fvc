from typing import cast

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import DomainError
from apps.stocks.infrastructure.repositories import (
    DjangoFinancialRepository,
    DjangoPriceRepository,
    DjangoStockRepository,
)

from ..application.dto import CalculateFairValueDTO, ReverseCalculateDTO
from ..application.services import ValuationService
from ..domain.entities import ValuationResult
from ..infrastructure.repositories import DjangoValuationRepository
from .serializers import CalculateFairValueSerializer, ReverseCalculateSerializer


def _get_valuation_service() -> ValuationService:
    return ValuationService(
        stock_repo=DjangoStockRepository(),
        financial_repo=DjangoFinancialRepository(),
        price_repo=DjangoPriceRepository(),
        valuation_repo=DjangoValuationRepository(),
    )


def _result_to_dict(r: ValuationResult) -> dict[str, object]:
    return {
        "id": r.id,
        "stock_id": r.stock_id,
        "growth_rate": str(r.growth_rate),
        "fair_pbr": str(r.fair_pbr),
        "fair_value": str(r.fair_value),
        "current_price": str(r.current_price),
        "discount_rate": str(r.discount_rate),
        "is_undervalued": r.is_undervalued,
        "roe": str(r.roe) if r.roe is not None else None,
        "cost_of_capital": str(r.cost_of_capital) if r.cost_of_capital is not None else None,
        "bps": str(r.bps) if r.bps is not None else None,
        "current_pbr": str(r.current_pbr) if r.current_pbr is not None else None,
        "implied_growth_rate": str(r.implied_growth_rate) if r.implied_growth_rate is not None else None,
    }


class ValuationCalculateView(APIView):
    """POST /api/valuations/calculate/ — 適正価格算出"""

    def post(self, request: Request) -> Response:
        serializer = CalculateFairValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _get_valuation_service()
        dto = CalculateFairValueDTO(**serializer.validated_data)
        try:
            result = service.calculate_fair_value(dto, user_id=cast("int", request.user.id))
        except DomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_result_to_dict(result), status=status.HTTP_201_CREATED)


class ValuationReverseCalculateView(APIView):
    """POST /api/valuations/reverse-calculate/ — 市場織り込み成長率逆算"""

    def post(self, request: Request) -> Response:
        serializer = ReverseCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _get_valuation_service()
        dto = ReverseCalculateDTO(**serializer.validated_data)
        try:
            result = service.reverse_calculate(dto)
        except DomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ValuationListView(APIView):
    """GET /api/valuations/ — 算出履歴一覧"""

    def get(self, request: Request) -> Response:
        service = _get_valuation_service()
        limit = int(request.query_params.get("limit", 50))
        results = service.list_valuations(user_id=cast("int", request.user.id), limit=limit)
        return Response([_result_to_dict(r) for r in results])


class ValuationDetailView(APIView):
    """GET /api/valuations/{id}/ — 算出結果詳細"""

    def get(self, request: Request, pk: int) -> Response:
        service = _get_valuation_service()
        try:
            result = service.get_valuation(pk, user_id=cast("int", request.user.id))
        except DomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(_result_to_dict(result))


class StockValuationListView(APIView):
    """GET /api/stocks/{code}/valuations/ — 銘柄別算出履歴"""

    def get(self, request: Request, code: str) -> Response:
        service = _get_valuation_service()
        try:
            results = service.list_by_stock(code, user_id=cast("int", request.user.id))
        except DomainError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response([_result_to_dict(r) for r in results])
