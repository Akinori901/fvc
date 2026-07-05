"""過去決算推移ツール UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.stocks.domain.repositories import FinancialRepository, StockRepository


class GetStockFinancialsToolUseCase:
    """過去 N 年分の財務データを返す。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo

    def execute(self, *, code: str, years: int = 5) -> dict[str, Any]:
        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {code}")

        financials = self._financial_repo.find_recent_by_stock_id(stock.id, limit=years)
        return {
            "code": stock.code,
            "name": stock.name,
            "years": [
                {
                    "fiscal_year": f.fiscal_year,
                    "period_end_date": f.period_end_date.isoformat() if f.period_end_date else None,
                    "bps": _decimal_or_none(f.bps),
                    "eps": _decimal_or_none(f.eps),
                    "roe": _decimal_or_none(f.roe),
                    "revenue": f.revenue,
                    "operating_income": f.operating_income,
                    "operating_cash_flow": f.operating_cash_flow,
                    "free_cash_flow": f.free_cash_flow,
                    "eps_forecast": _decimal_or_none(f.eps_forecast),
                }
                for f in financials
            ],
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
