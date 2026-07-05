"""手動財務データ入力 API ビュー。

J-Quants で取得できないデータを補完するためのエンドポイント。
J-Quants 同期時に同年度の自動データが登録されると t_stock_financials が優先され、
このテーブルのデータは参照されなくなる（削除はしない）。
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stocks.models import FinancialManualInput, Stock, StockFinancial
from apps.valuations.domain.entities import MARKET_COST_OF_CAPITAL, FairValueCalculation

if TYPE_CHECKING:
    from rest_framework.request import Request


def _parse_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _try_calculate(
    stock: Stock,
    fiscal_year: int,
    bps: Decimal | None,
    eps: Decimal | None,
    roe_raw: Decimal | None,
    growth_rate: Decimal = Decimal("0.05"),
) -> dict[str, str] | None:
    """財務データと株価から適正株価を即時計算して返す。計算不可の場合は None。"""
    if stock.latest_price is None or bps is None or bps <= 0:
        return None

    # ROE の決定 (EPS/BPS 優先、なければ roe フィールド)
    if eps is not None and bps and bps != 0:
        roe = eps / bps
    elif roe_raw is not None:
        roe = roe_raw
    else:
        return None

    cost_of_capital = MARKET_COST_OF_CAPITAL.get(stock.market_type, MARKET_COST_OF_CAPITAL["JP"])
    if growth_rate >= cost_of_capital or roe <= growth_rate or roe <= 0:
        return None

    try:
        calc = FairValueCalculation(
            growth_rate=growth_rate,
            bps=bps,
            current_price=stock.latest_price,
            roe=roe,
            cost_of_capital=cost_of_capital,
        )
        return {
            "fair_pbr": str(calc.fair_pbr),
            "fair_value": str(calc.fair_value),
            "discount_rate": str(calc.discount_rate),
            "current_pbr": str(calc.current_pbr),
        }
    except Exception:
        return None


class ManualFinancialListView(APIView):
    """GET /api/stocks/{code}/financials/manual/  — 一覧
    POST /api/stocks/{code}/financials/manual/ — 登録・更新
    """

    permission_classes = [IsAuthenticated]

    def _get_stock(self, code: str) -> Stock | None:
        try:
            return Stock.objects.get(code=code)
        except Stock.DoesNotExist:
            return None

    def get(self, request: Request, code: str) -> Response:
        stock = self._get_stock(code)
        if stock is None:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)

        manuals = FinancialManualInput.objects.filter(stock=stock).order_by("-fiscal_year")
        # J-Quants で取得済みかどうかのフラグも付与
        auto_years = set(StockFinancial.objects.filter(stock=stock).values_list("fiscal_year", flat=True))
        data = [
            {
                "fiscal_year": m.fiscal_year,
                "bps": str(m.bps) if m.bps is not None else None,
                "eps": str(m.eps) if m.eps is not None else None,
                "roe": str(m.roe) if m.roe is not None else None,
                "eps_forecast": str(m.eps_forecast) if m.eps_forecast is not None else None,
                "revenue": m.revenue,
                "operating_income": m.operating_income,
                "source": m.source,
                "source_label": m.get_source_display(),
                "note": m.note,
                "is_overridden_by_auto": m.fiscal_year in auto_years,
                "updated_at": m.updated_at.isoformat(),
            }
            for m in manuals
        ]
        return Response(data)

    def post(self, request: Request, code: str) -> Response:
        stock = self._get_stock(code)
        if stock is None:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)

        fiscal_year = request.data.get("fiscal_year")
        if fiscal_year is None:
            return Response({"detail": "fiscal_year は必須です"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fiscal_year = int(fiscal_year)
        except (TypeError, ValueError):
            return Response({"detail": "fiscal_year は整数で指定してください"}, status=status.HTTP_400_BAD_REQUEST)

        bps = _parse_decimal(request.data.get("bps"))
        eps = _parse_decimal(request.data.get("eps"))
        roe_raw = _parse_decimal(request.data.get("roe"))
        eps_forecast = _parse_decimal(request.data.get("eps_forecast"))
        revenue = _parse_int(request.data.get("revenue"))
        operating_income = _parse_int(request.data.get("operating_income"))
        source = request.data.get("source", "other")
        note = request.data.get("note", "")

        obj, created = FinancialManualInput.objects.update_or_create(
            stock=stock,
            fiscal_year=fiscal_year,
            defaults={
                "bps": bps,
                "eps": eps,
                "roe": roe_raw,
                "eps_forecast": eps_forecast,
                "revenue": revenue,
                "operating_income": operating_income,
                "source": source,
                "note": note,
            },
        )

        # J-Quants 同年度データがあるか確認
        auto_exists = StockFinancial.objects.filter(stock=stock, fiscal_year=fiscal_year).exists()

        # 即時計算
        growth_rate_param = _parse_decimal(request.data.get("growth_rate")) or Decimal("0.05")
        calculation = _try_calculate(stock, fiscal_year, bps, eps, roe_raw, growth_rate_param)

        financial_data = {
            "fiscal_year": fiscal_year,
            "bps": str(bps) if bps is not None else None,
            "eps": str(eps) if eps is not None else None,
            "roe": str(roe_raw) if roe_raw is not None else None,
            "eps_forecast": str(eps_forecast) if eps_forecast is not None else None,
            "revenue": revenue,
            "operating_income": operating_income,
            "source": source,
            "source_label": obj.get_source_display(),
            "note": note,
            "is_manual": True,
            "is_overridden_by_auto": auto_exists,
        }

        return Response(
            {"financial": financial_data, "calculation": calculation},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ManualFinancialDetailView(APIView):
    """DELETE /api/stocks/{code}/financials/manual/{fiscal_year}/"""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, code: str, fiscal_year: int) -> Response:
        try:
            stock = Stock.objects.get(code=code)
        except Stock.DoesNotExist:
            return Response({"detail": f"銘柄が見つかりません: {code}"}, status=status.HTTP_404_NOT_FOUND)

        deleted, _ = FinancialManualInput.objects.filter(stock=stock, fiscal_year=fiscal_year).delete()
        if deleted == 0:
            return Response({"detail": "手動財務データが見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
