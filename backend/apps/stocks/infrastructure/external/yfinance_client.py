"""yfinance ラッパークライアント。"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.stocks.domain.repositories import (
    MarketDataProvider,
    MarketDividendData,
    MarketFinancialData,
    MarketPriceData,
    MarketStockData,
)

logger = logging.getLogger(__name__)


class YfinanceClient(MarketDataProvider):
    """yfinance を使用した市場データプロバイダー。

    - JP株: ``"7203.T"`` 形式でティッカー指定
    - US株: ``"AAPL"`` 形式
    - ``fetch_stock_list()`` は空リスト（yfinance は銘柄一覧API非対応）
    """

    def get_provider_name(self) -> str:
        return "yfinance"

    # ------------------------------------------------------------------
    # 銘柄一覧
    # ------------------------------------------------------------------

    def fetch_stock_list(self) -> list[MarketStockData]:
        """yfinance は銘柄一覧を提供しないため空リストを返す。"""
        return []

    # ------------------------------------------------------------------
    # 財務データ
    # ------------------------------------------------------------------

    def fetch_financials(self, code: str, fiscal_year: int | None = None) -> list[MarketFinancialData]:
        """財務データを取得。"""
        import yfinance as yf

        ticker_symbol = _to_yfinance_ticker(code)
        ticker = yf.Ticker(ticker_symbol)

        results: list[MarketFinancialData] = []

        try:
            balance_sheet = ticker.balance_sheet
            income_stmt = ticker.income_stmt
            cash_flow_stmt = ticker.cash_flow
        except Exception:
            logger.warning("yfinance: %s の財務データ取得に失敗", code, exc_info=True)
            return []

        if balance_sheet is None or balance_sheet.empty:
            return []

        for col in balance_sheet.columns:
            fy = col.year
            if fiscal_year is not None and fy != fiscal_year:
                continue

            # BPS = 純資産 / 発行済株式数
            _get_bs_value(
                balance_sheet,
                col,
                ["Stockholders Equity", "Total Equity Gross Minority Interest", "Ordinary Shares Number"],
            )
            shares_outstanding = _get_value(balance_sheet, col, ["Ordinary Shares Number", "Share Issued"])

            net_assets_raw = _get_value(
                balance_sheet, col, ["Stockholders Equity", "Total Equity Gross Minority Interest"]
            )
            total_equity_val = _safe_decimal(net_assets_raw)

            shares_val = _safe_int(shares_outstanding)

            bps: Decimal | None = None
            if total_equity_val and shares_val and shares_val > 0:
                bps = total_equity_val / Decimal(shares_val)

            if bps is None:
                continue

            # EPS, 売上高, 営業利益
            eps: Decimal | None = None
            revenue_raw = None
            op_income_raw = None
            net_income_raw = None

            if income_stmt is not None and not income_stmt.empty and col in income_stmt.columns:
                net_income_raw = _get_value(income_stmt, col, ["Net Income", "Net Income Common Stockholders"])
                revenue_raw = _get_value(income_stmt, col, ["Total Revenue", "Operating Revenue"])
                op_income_raw = _get_value(income_stmt, col, ["Operating Income", "EBIT"])

                if net_income_raw is not None and shares_val and shares_val > 0:
                    ni = _safe_decimal(net_income_raw)
                    if ni is not None:
                        eps = ni / Decimal(shares_val)

            # ROE = 当期純利益 / 純資産
            roe: Decimal | None = None
            if net_income_raw is not None and total_equity_val and total_equity_val != 0:
                ni = _safe_decimal(net_income_raw)
                if ni is not None:
                    roe = ni / total_equity_val

            # キャッシュフロー
            ocf_raw = None
            fcf_raw = None
            if cash_flow_stmt is not None and not cash_flow_stmt.empty and col in cash_flow_stmt.columns:
                ocf_raw = _get_value(cash_flow_stmt, col, ["Operating Cash Flow"])
                fcf_raw = _get_value(cash_flow_stmt, col, ["Free Cash Flow"])

            results.append(
                MarketFinancialData(
                    code=code,
                    fiscal_year=fy,
                    bps=bps,
                    eps=eps,
                    roe=roe,
                    net_assets=_to_millions(net_assets_raw),
                    total_shares=_safe_int(shares_outstanding),
                    revenue=_to_millions(revenue_raw),
                    operating_income=_to_millions(op_income_raw),
                    operating_cash_flow=_to_millions(ocf_raw),
                    free_cash_flow=_to_millions(fcf_raw),
                )
            )

        logger.info("yfinance: %s の財務データ %d 件を取得", code, len(results))
        return results

    # ------------------------------------------------------------------
    # 株価
    # ------------------------------------------------------------------

    def fetch_prices(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketPriceData]:
        """日足株価データを取得。"""
        import yfinance as yf

        ticker_symbol = _to_yfinance_ticker(code)
        ticker = yf.Ticker(ticker_symbol)

        kwargs: dict[str, str] = {}
        if from_date:
            kwargs["start"] = from_date.isoformat()
        if to_date:
            kwargs["end"] = to_date.isoformat()

        if not kwargs:
            kwargs["period"] = "1y"

        try:
            hist = ticker.history(**kwargs)
        except Exception:
            logger.warning("yfinance: %s の株価取得に失敗", code, exc_info=True)
            return []

        if hist is None or hist.empty:
            return []

        results: list[MarketPriceData] = []
        for idx, row in hist.iterrows():
            close_val = row.get("Close")
            if close_val is None:
                continue
            close_dec = _safe_decimal(close_val)
            if close_dec is None:
                continue

            price_date = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
            volume_val = _safe_int(row.get("Volume"))

            results.append(
                MarketPriceData(
                    code=code,
                    date=price_date,
                    close_price=close_dec,
                    volume=volume_val,
                )
            )

        logger.info("yfinance: %s の株価 %d 件を取得", code, len(results))
        return results

    # ------------------------------------------------------------------
    # 配当・分配金
    # ------------------------------------------------------------------

    def supports_dividend_fetch(self) -> bool:
        return True

    def fetch_dividends(self, code: str) -> list[MarketDividendData]:
        """配当・分配金履歴を取得。ETF・REITの分配金も含む。"""
        import yfinance as yf

        ticker_symbol = _to_yfinance_ticker(code)
        ticker = yf.Ticker(ticker_symbol)

        try:
            divs = ticker.dividends  # pd.Series: {Timestamp: amount}
        except Exception:
            logger.warning("yfinance: %s の配当データ取得に失敗", code, exc_info=True)
            return []

        if divs is None or divs.empty:
            return []

        results: list[MarketDividendData] = []
        for ts, amount in divs.items():
            amount_dec = _safe_decimal(amount)
            if amount_dec is None or amount_dec <= 0:
                continue
            ex_date = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
            results.append(
                MarketDividendData(
                    code=code,
                    ex_dividend_date=ex_date,
                    dividends_per_share=amount_dec,
                )
            )

        logger.info("yfinance: %s の配当データ %d 件を取得", code, len(results))
        return results


# ============================================================
# ヘルパー関数
# ============================================================


def _to_yfinance_ticker(code: str) -> str:
    """銘柄コードを yfinance ティッカーシンボルに変換。

    - 4桁の数字 → JP株とみなし ``.T`` を付与
    - 5桁で末尾0 → 4桁化して ``.T``
    - それ以外 → そのまま（US株等）
    """
    if code.isdigit():
        if len(code) == 5 and code.endswith("0"):
            code = code[:4]
        return f"{code}.T"
    return code


def _get_value(df: Any, col: Any, keys: list[str]) -> Any | None:
    """DataFrameから複数の候補キーで値を取得。"""
    for key in keys:
        try:
            if key in df.index:
                val = df.loc[key, col]
                if val is not None and str(val) not in ("nan", "NaN", ""):
                    return val
        except (KeyError, TypeError):
            continue
    return None


def _get_bs_value(df: Any, col: Any, keys: list[str]) -> Any | None:
    """_get_value のエイリアス（バランスシート用）。"""
    return _get_value(df, col, keys)


def _safe_decimal(value: object) -> Decimal | None:
    """安全にDecimalへ変換。"""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if s in ("", "nan", "NaN", "-", "None", "inf", "-inf"):
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _safe_int(value: object) -> int | None:
    """安全にintへ変換。"""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if s in ("", "nan", "NaN", "-", "None"):
            return None
        return int(float(s))
    except (ValueError, OverflowError):
        return None


def _to_millions(value: object) -> int | None:
    """値を百万単位のintに変換。"""
    raw = _safe_int(value)
    if raw is None:
        return None
    return raw // 1_000_000
