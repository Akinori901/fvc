from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import EntityNotFoundError

from ..application.dto import CreateFinancialDTO, CreateStockDTO, UpdateStockDTO
from ..application.services import FinancialService, StockService
from ..infrastructure.repositories import (
    DjangoDividendRepository,
    DjangoFinancialRepository,
    DjangoOwnerShareholderRepository,
    DjangoStockRepository,
)
from .serializers import StockFinancialCreateSerializer, StockSerializer


def _get_stock_service() -> StockService:
    return StockService(stock_repo=DjangoStockRepository())


def _get_financial_service() -> FinancialService:
    return FinancialService(
        stock_repo=DjangoStockRepository(),
        financial_repo=DjangoFinancialRepository(),
    )


class StockListView(APIView):
    """GET /api/stocks/ — 銘柄一覧 / POST — 銘柄登録"""

    def get(self, request: Request) -> Response:
        service = _get_stock_service()
        stocks = service.list_stocks()
        data = [
            {
                "id": s.id,
                "code": s.code,
                "name": s.name,
                "market": s.market,
                "sector": s.sector,
                "latest_price": str(s.latest_price) if s.latest_price else None,
                "latest_price_date": str(s.latest_price_date) if s.latest_price_date else None,
            }
            for s in stocks
        ]
        return Response(data)

    def post(self, request: Request) -> Response:
        serializer = StockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _get_stock_service()
        dto = CreateStockDTO(**serializer.validated_data)
        stock = service.create_stock(dto)
        return Response(
            {"id": stock.id, "code": stock.code, "name": stock.name, "market": stock.market, "sector": stock.sector},
            status=status.HTTP_201_CREATED,
        )


class StockDetailView(APIView):
    """GET/PUT/DELETE /api/stocks/{code}/"""

    def get(self, request: Request, code: str) -> Response:
        service = _get_stock_service()
        try:
            stock = service.get_stock(code)
        except EntityNotFoundError:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)

        result: dict[str, object] = {
            "id": stock.id,
            "code": stock.code,
            "name": stock.name,
            "market": stock.market,
            "market_type": stock.market_type,
            "sector": stock.sector,
            "is_active": stock.is_active,
            "instrument_type": getattr(stock, "instrument_type", "stock"),
            "latest_price": str(stock.latest_price) if stock.latest_price else None,
            "latest_price_date": str(stock.latest_price_date) if stock.latest_price_date else None,
        }

        # 配当メトリクス
        if stock.id is not None:
            try:
                from ..domain.dividend_metrics import compute_dividend_metrics

                div_repo = DjangoDividendRepository()
                fin_repo = DjangoFinancialRepository()
                annual_total = div_repo.find_annual_total(stock.id)
                dividends = div_repo.find_by_stock_id(stock.id, limit=500)
                latest_fin = fin_repo.find_latest_by_stock_id(stock.id)
                dm = compute_dividend_metrics(
                    dividends=dividends,
                    annual_total=annual_total,
                    latest_price=stock.latest_price,
                    eps=latest_fin.eps if latest_fin else None,
                )
                result["dividend_yield"] = str(dm.dividend_yield) if dm.dividend_yield is not None else None
                result["payout_ratio"] = str(dm.payout_ratio) if dm.payout_ratio is not None else None
                result["consecutive_dividend_years"] = dm.consecutive_dividend_years
                result["progressive_dividend_years"] = dm.progressive_dividend_years
                result["dividend_score"] = dm.dividend_score
            except Exception:
                pass

            # FCFメトリクス
            try:
                from ..domain.fcf_metrics import compute_fcf_metrics

                if latest_fin is None:
                    fin_repo_fcf = DjangoFinancialRepository()
                    latest_fin = fin_repo_fcf.find_latest_by_stock_id(stock.id)
                recent_fins = DjangoFinancialRepository().find_by_stock_id(stock.id)
                prev_fcf = recent_fins[1].free_cash_flow if len(recent_fins) >= 2 else None  # noqa: PLR2004
                market_cap = None
                if stock.latest_price and latest_fin and latest_fin.total_shares:
                    from decimal import Decimal

                    market_cap = stock.latest_price * Decimal(latest_fin.total_shares)
                fm = compute_fcf_metrics(
                    latest_fcf=latest_fin.free_cash_flow if latest_fin else None,
                    prev_fcf=prev_fcf,
                    market_cap=market_cap,
                    revenue=latest_fin.revenue if latest_fin else None,
                )
                result["fcf"] = fm.fcf
                result["fcf_yield"] = str(fm.fcf_yield) if fm.fcf_yield is not None else None
                result["fcf_margin"] = str(fm.fcf_margin) if fm.fcf_margin is not None else None
                result["fcf_score"] = fm.fcf_score
            except Exception:
                pass

            # オーナー経営指標
            try:
                owner_repo = DjangoOwnerShareholderRepository()
                owners = owner_repo.find_by_stock_id(stock.id)
                if owners:
                    _type_priority = {"exact": 0, "family": 1, "company": 2}
                    total_ratio = sum(o.ownership_ratio for o in owners)
                    best_type = min(owners, key=lambda o: _type_priority.get(o.match_type, 99)).match_type
                    result["is_owner_managed"] = True
                    result["owner_ratio"] = str(total_ratio)
                    result["owner_match_type"] = best_type
                    result["owner_shareholders"] = [
                        {
                            "shareholder_name": o.shareholder_name,
                            "ownership_ratio": str(o.ownership_ratio),
                            "match_type": o.match_type,
                            "rank": o.shareholder_rank,
                        }
                        for o in owners
                    ]
                    result["representative_name"] = owners[0].representative_name
                else:
                    result["is_owner_managed"] = False
            except Exception:
                pass

            # 業界平均推計（業界下限ROEでの保守シナリオ適正株価）
            try:
                from decimal import Decimal

                from apps.valuations.domain.entities import (
                    MARKET_COST_OF_CAPITAL,
                    FairValueCalculation,
                )
                from config import container as _container

                industry_repo = _container.industry_metrics_repository()
                metrics = industry_repo.find_by_sector(stock.sector) if stock.sector else None
                if (
                    metrics
                    and latest_fin
                    and latest_fin.bps
                    and stock.latest_price
                    and metrics.min_roe > Decimal("0.02")
                ):
                    effective_bps = latest_fin.bps * latest_fin.adj_factor
                    cost_of_capital = MARKET_COST_OF_CAPITAL.get(stock.market_type, Decimal("0.08"))
                    calc = FairValueCalculation(
                        growth_rate=Decimal("0.02"),
                        bps=effective_bps,
                        current_price=stock.latest_price,
                        roe=metrics.min_roe,
                        cost_of_capital=cost_of_capital,
                    )
                    result["industry_metrics"] = {
                        "sector": metrics.sector,
                        "min_roe": str(metrics.min_roe),
                        "max_roe": str(metrics.max_roe),
                        "min_roe_fair_value": str(calc.fair_value),
                        "min_roe_fair_pbr": str(calc.fair_pbr),
                    }
            except Exception:
                pass

            # スクリーニング系メトリクス（評価ゾーン・成長率ラベル等）— ヘッダーバッジ表示用
            try:
                from decimal import Decimal

                from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
                from config import container as _container2

                screening_usecase = ScreeningUseCase(
                    stock_repo=_container2.stock_repository(),
                    financial_repo=_container2.financial_repository(),
                    margin_repo=_container2.margin_repository(),
                    price_repo=_container2.price_repository(),
                    dividend_repo=_container2.dividend_repository(),
                    owner_repo=_container2.owner_shareholder_repository(),
                )
                screening_results = screening_usecase.execute(
                    growth_rate=Decimal("0.02"),
                    market_type=stock.market_type or "JP",
                    code=stock.code,
                )
                sr = screening_results[0] if screening_results else None
                if sr is not None:
                    result["evaluation_zone"] = sr.evaluation_zone
                    result["growth_rate_label"] = sr.growth_rate_label
                    result["roe_trend"] = sr.roe_trend
                    result["eps_growth_yoy"] = str(sr.eps_growth_yoy) if sr.eps_growth_yoy is not None else None
                    result["eps_cagr_3y"] = str(sr.eps_cagr_3y) if sr.eps_cagr_3y is not None else None
                    result["sl_ratio"] = str(sr.sl_ratio) if sr.sl_ratio is not None else None
            except Exception:
                pass

        return Response(result)

    def put(self, request: Request, code: str) -> Response:
        service = _get_stock_service()
        dto = UpdateStockDTO(
            name=request.data.get("name"),
            market=request.data.get("market"),
            sector=request.data.get("sector"),
        )
        try:
            stock = service.update_stock(code, dto)
        except EntityNotFoundError:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {"id": stock.id, "code": stock.code, "name": stock.name, "market": stock.market, "sector": stock.sector}
        )

    def delete(self, request: Request, code: str) -> Response:
        service = _get_stock_service()
        try:
            service.delete_stock(code)
        except EntityNotFoundError:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class StockFinancialListView(APIView):
    """GET/POST /api/stocks/{code}/financials/"""

    def get(self, request: Request, code: str) -> Response:
        service = _get_financial_service()
        try:
            financials = service.list_financials(code)
        except EntityNotFoundError:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        data = [
            {
                "id": f.id,
                "fiscal_year": f.fiscal_year,
                "bps": str(f.bps),
                "eps": str(f.eps) if f.eps else None,
                "roe": str(f.roe) if f.roe else None,
                "net_assets": f.net_assets,
                "total_shares": f.total_shares,
                "revenue": f.revenue,
                "eps_forecast": str(f.eps_forecast) if f.eps_forecast else None,
                "adj_factor": str(f.adj_factor),
            }
            for f in financials
        ]
        return Response(data)

    def post(self, request: Request, code: str) -> Response:
        serializer = StockFinancialCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _get_financial_service()
        dto = CreateFinancialDTO(stock_code=code, **serializer.validated_data)
        try:
            financial = service.create_financial(dto)
        except EntityNotFoundError:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": financial.id,
                "fiscal_year": financial.fiscal_year,
                "bps": str(financial.bps),
                "eps": str(financial.eps) if financial.eps else None,
                "roe": str(financial.roe) if financial.roe else None,
            },
            status=status.HTTP_201_CREATED,
        )


class StockPriceListView(APIView):
    """GET /api/stocks/{code}/prices/"""

    def get(self, request: Request, code: str) -> Response:
        from ..infrastructure.repositories import DjangoPriceRepository, DjangoStockRepository

        stock_repo = DjangoStockRepository()
        stock = stock_repo.find_by_code(code)
        if stock is None:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        assert stock.id is not None
        price_repo = DjangoPriceRepository()
        limit = int(request.query_params.get("limit", 100))
        prices = price_repo.find_by_stock_id(stock.id, limit=limit)
        data = [
            {"id": p.id, "date": p.date, "close_price": str(p.close_price), "pbr": str(p.pbr) if p.pbr else None}
            for p in prices
        ]
        return Response(data)


class StockDividendListView(APIView):
    """GET /api/stocks/{code}/dividends/"""

    def get(self, request: Request, code: str) -> Response:
        from ..infrastructure.repositories import DjangoDividendRepository, DjangoStockRepository

        stock_repo = DjangoStockRepository()
        stock = stock_repo.find_by_code(code)
        if stock is None:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)
        assert stock.id is not None
        dividend_repo = DjangoDividendRepository()
        limit = int(request.query_params.get("limit", 50))
        dividends = dividend_repo.find_by_stock_id(stock.id, limit=limit)
        data = [
            {
                "date": d.ex_dividend_date.isoformat(),
                "amount": str(d.dividends_per_share),
                "source": d.source,
            }
            for d in dividends
        ]
        return Response(data)
