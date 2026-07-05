"""J-Quants API クライアント（公式SDK jquantsapi ラッパー）。"""

from __future__ import annotations

import contextlib
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from apps.stocks.domain.repositories import (
    MarketDataProvider,
    MarketDividendData,
    MarketFinancialData,
    MarketMarginData,
    MarketPriceData,
    MarketStockData,
)

logger = logging.getLogger(__name__)


class JQuantsClient(MarketDataProvider):
    """J-Quants API を使用した市場データプロバイダー。

    公式Python SDK (jquantsapi) を利用。
    認証は API Key 方式（V2 API）。
    """

    _MAX_RETRIES = 3
    _BASE_DELAY = 5  # seconds

    def __init__(self, api_key: str, plan: str = "standard") -> None:
        import jquantsapi

        self._client = jquantsapi.ClientV2(api_key=api_key)
        self._plan = plan

    def get_provider_name(self) -> str:
        return "jquants"

    def _call_with_backoff(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """SDK メソッドを指数バックオフ付きで呼び出す。

        SDK 内部の Retry は backoff_factor=0 のため、429 時に即座に
        リトライを消費してしまう。アプリケーション層で再試行する。
        """
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) and attempt < self._MAX_RETRIES:
                    delay = self._BASE_DELAY * (2**attempt)
                    logger.warning(
                        "J-Quants 429 rate limit, %ds 後にリトライ (%d/%d)",
                        delay,
                        attempt + 1,
                        self._MAX_RETRIES,
                    )
                    time.sleep(delay)
                else:
                    raise

    def fetch_stock_list(self) -> list[MarketStockData]:
        """上場銘柄一覧を取得。"""
        df = self._call_with_backoff(self._client.get_list)
        results: list[MarketStockData] = []
        for _, row in df.iterrows():
            code = str(row.get("Code", ""))
            if not code:
                continue
            # J-Quantsの証券コードは5桁（末尾0）の場合がある。4桁に正規化
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]
            name = str(row.get("CoName", ""))
            market = str(row.get("MktNm", ""))
            results.append(
                MarketStockData(
                    code=code,
                    name=name,
                    market=market,
                    market_type="JP",
                    sector=str(row.get("S33Nm", "")),
                    instrument_type=_detect_instrument_type(name, market),
                )
            )
        logger.info("J-Quants: %d 銘柄を取得", len(results))
        return results

    def fetch_financials(self, code: str, fiscal_year: int | None = None) -> list[MarketFinancialData]:
        """財務データを取得。"""
        # J-Quantsの証券コードは5桁形式
        jquants_code = code if len(code) == 5 else f"{code}0"
        df = self._call_with_backoff(self._client.get_fin_summary, code=jquants_code)
        if df.empty:
            return []
        df = df.sort_values("CurPerEn", ascending=True)

        results: list[MarketFinancialData] = []
        for _, row in df.iterrows():
            # 会計年度の抽出（CurPerEn = CurrentPeriodEndDate）
            period_end = str(row.get("CurPerEn", ""))
            if not period_end or len(period_end) < 4:
                continue
            fy = int(period_end[:4])
            if fiscal_year is not None and fy != fiscal_year:
                continue

            bps_val = row.get("BPS")
            if bps_val is None or str(bps_val) in ("", "nan", "-"):
                continue

            # 決算期末日（株式分割調整係数の基準日として保存）
            period_end_dt: date | None = None
            try:
                period_end_dt = date.fromisoformat(period_end[:10]) if period_end else None
            except ValueError:
                period_end_dt = None

            results.append(
                MarketFinancialData(
                    code=code,
                    fiscal_year=fy,
                    bps=_to_decimal(bps_val),
                    eps=_derive_eps(row),
                    roe=_to_decimal_or_none(row.get("EqAR")),
                    net_assets=_to_int_millions_or_none(row.get("Eq")),
                    total_shares=_to_int_or_none(row.get("ShOutFY")),
                    revenue=_to_int_millions_or_none(row.get("Sales")),
                    operating_income=_to_int_millions_or_none(row.get("OP")),
                    eps_forecast=_derive_feps(row),
                    period_end_date=period_end_dt,
                )
            )
        logger.info("J-Quants: %s の財務データ %d 件を取得", code, len(results))
        return results

    def fetch_prices(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketPriceData]:
        """日足株価データを取得。"""
        jquants_code = code if len(code) == 5 else f"{code}0"

        kwargs: dict[str, object] = {"code": jquants_code}
        if from_date:
            kwargs["from_yyyymmdd"] = from_date.strftime("%Y%m%d")
        if to_date:
            kwargs["to_yyyymmdd"] = to_date.strftime("%Y%m%d")

        df = self._call_with_backoff(self._client.get_eq_bars_daily, **kwargs)
        if df.empty:
            return []

        results: list[MarketPriceData] = []
        for _, row in df.iterrows():
            date_str = str(row.get("Date", ""))[:10]  # 'YYYY-MM-DD HH:MM:SS' → 'YYYY-MM-DD'
            close_val = row.get("AdjC")  # 権利調整済み終値
            if not date_str or date_str == "nan" or close_val is None or str(close_val) in ("", "nan"):
                continue
            results.append(
                MarketPriceData(
                    code=code,
                    date=date.fromisoformat(date_str),
                    close_price=_to_decimal(close_val),
                    volume=_to_int_or_none(row.get("AdjVo")),
                    adj_factor=_to_adj_factor(row.get("AdjFactor")),
                    is_limit_up=_to_bool_flag(row.get("UL")),
                    is_limit_down=_to_bool_flag(row.get("LL")),
                )
            )
        logger.info("J-Quants: %s の株価 %d 件を取得", code, len(results))
        return results

    # ------------------------------------------------------------------
    # 一括取得メソッド
    # ------------------------------------------------------------------

    def supports_bulk_fetch(self) -> bool:
        return True

    def fetch_all_prices(self, target_date: date) -> list[MarketPriceData]:
        """指定日の全銘柄株価を一括取得。"""
        date_str = target_date.strftime("%Y%m%d")
        df = self._call_with_backoff(self._client.get_eq_bars_daily, date_yyyymmdd=date_str)
        if df is None or df.empty:
            return []

        results: list[MarketPriceData] = []
        for _, row in df.iterrows():
            code = str(row.get("Code", ""))
            if not code:
                continue
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]

            date_val = str(row.get("Date", ""))[:10]  # 'YYYY-MM-DD HH:MM:SS' → 'YYYY-MM-DD'
            close_val = row.get("AdjC")  # 権利調整済み終値
            if not date_val or date_val == "nan" or close_val is None or str(close_val) in ("", "nan"):
                continue

            results.append(
                MarketPriceData(
                    code=code,
                    date=date.fromisoformat(date_val),
                    close_price=_to_decimal(close_val),
                    volume=_to_int_or_none(row.get("AdjVo")),
                    adj_factor=_to_adj_factor(row.get("AdjFactor")),
                    is_limit_up=_to_bool_flag(row.get("UL")),
                    is_limit_down=_to_bool_flag(row.get("LL")),
                )
            )
        logger.info("J-Quants: 全銘柄株価 %d 件を一括取得 (date=%s)", len(results), target_date)
        return results

    def fetch_all_financials(self, from_date: date, to_date: date) -> list[MarketFinancialData]:
        """期間内の全銘柄財務データを一括取得。"""
        df = self._call_with_backoff(self._client.get_fin_summary_range, start_dt=from_date, end_dt=to_date)
        if df is None or df.empty:
            return []
        df = df.sort_values("CurPerEn", ascending=True)

        results: list[MarketFinancialData] = []
        for _, row in df.iterrows():
            code = str(row.get("Code", ""))
            if not code:
                continue
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]

            period_end = str(row.get("CurPerEn", ""))
            if not period_end or len(period_end) < 4:
                continue
            fy = int(period_end[:4])

            bps_val = row.get("BPS")
            if bps_val is None or str(bps_val) in ("", "nan", "-"):
                continue

            period_end_raw = str(row.get("CurPerEn", ""))
            try:
                period_end_dt = date.fromisoformat(period_end_raw[:10]) if period_end_raw else None
            except ValueError:
                period_end_dt = None

            results.append(
                MarketFinancialData(
                    code=code,
                    fiscal_year=fy,
                    bps=_to_decimal(bps_val),
                    eps=_derive_eps(row),
                    roe=_to_decimal_or_none(row.get("EqAR")),
                    net_assets=_to_int_millions_or_none(row.get("Eq")),
                    total_shares=_to_int_or_none(row.get("ShOutFY")),
                    revenue=_to_int_millions_or_none(row.get("Sales")),
                    operating_income=_to_int_millions_or_none(row.get("OP")),
                    eps_forecast=_derive_feps(row),
                    period_end_date=period_end_dt,
                )
            )
        logger.info(
            "J-Quants: 全銘柄財務データ %d 件を一括取得 (%s〜%s)",
            len(results),
            from_date,
            to_date,
        )
        return results

    # ------------------------------------------------------------------
    # 配当・分配金（Premium プランのみ対応）
    # ------------------------------------------------------------------

    def supports_dividend_fetch(self) -> bool:
        return self._plan == "premium"

    # ------------------------------------------------------------------
    # 信用取引残高（Standard 以上で利用可能）
    # ------------------------------------------------------------------

    def supports_margin_fetch(self) -> bool:
        return True

    def fetch_margin_balance(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketMarginData]:
        """信用取引週末残高を取得（制度信用 + 一般信用の合算）。

        get_mkt_margin_interest（/markets/margin-interest）を使用。
        全東証上場銘柄対象・週次データ（Standardプラン以上）。
        """
        jquants_code = code if len(code) == 5 else f"{code}0"
        kwargs: dict[str, object] = {"code": jquants_code}
        if from_date:
            kwargs["from_yyyymmdd"] = from_date.strftime("%Y%m%d")
        if to_date:
            kwargs["to_yyyymmdd"] = to_date.strftime("%Y%m%d")

        try:
            df = self._call_with_backoff(self._client.get_mkt_margin_interest, **kwargs)
        except Exception as e:
            logger.warning("J-Quants: %s の信用残高取得に失敗: %s", code, e)
            return []
        if df is None or df.empty:
            return []

        # 制度信用・一般信用を日付ごとに合算
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        grouped = df.groupby("Date").agg(LongVol=("LongVol", "sum"), ShrtVol=("ShrtVol", "sum")).reset_index()

        results: list[MarketMarginData] = []
        for _, row in grouped.iterrows():
            long_vol = _to_int_or_none(row.get("LongVol"))
            shrt_vol = _to_int_or_none(row.get("ShrtVol"))
            sl_ratio: Decimal | None = None
            if long_vol and long_vol > 0 and shrt_vol is not None:
                with contextlib.suppress(Exception):
                    sl_ratio = (Decimal(str(shrt_vol)) / Decimal(str(long_vol))).quantize(Decimal("0.0001"))
            results.append(
                MarketMarginData(
                    code=code,
                    date=row["Date"],
                    long_balance=long_vol,
                    long_balance_change=None,  # 週次データには変化量なし
                    short_balance=shrt_vol,
                    short_balance_change=None,
                    sl_ratio=sl_ratio,
                )
            )
        logger.info("J-Quants: %s の信用残高 %d 件を取得", code, len(results))
        return results

    def fetch_all_margin_balance(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketMarginData]:
        """全銘柄の信用取引週末残高を一括取得。get_mkt_margin_interest_range を使用。

        per-stock API（4439回）の代わりに1回のAPIコールで全銘柄分を取得する。
        """
        from datetime import timedelta

        start = from_date or (date.today() - timedelta(days=90))
        end = to_date or date.today()
        try:
            df = self._call_with_backoff(self._client.get_mkt_margin_interest_range, start_dt=start, end_dt=end)
        except Exception as e:
            logger.warning("J-Quants: 信用残高一括取得に失敗: %s", e)
            return []
        if df is None or df.empty:
            return []

        # 5桁コード → 4桁コードへの変換（58920 → 5892）
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        df["code4"] = df["Code"].astype(str).str[:4]

        # 制度信用・一般信用を (code, date) ごとに合算
        grouped = (
            df.groupby(["code4", "Date"]).agg(LongVol=("LongVol", "sum"), ShrtVol=("ShrtVol", "sum")).reset_index()
        )

        results: list[MarketMarginData] = []
        for _, row in grouped.iterrows():
            long_vol = _to_int_or_none(row.get("LongVol"))
            shrt_vol = _to_int_or_none(row.get("ShrtVol"))
            sl_ratio: Decimal | None = None
            if long_vol and long_vol > 0 and shrt_vol is not None:
                with contextlib.suppress(Exception):
                    sl_ratio = (Decimal(str(shrt_vol)) / Decimal(str(long_vol))).quantize(Decimal("0.0001"))
            results.append(
                MarketMarginData(
                    code=str(row["code4"]),
                    date=row["Date"],
                    long_balance=long_vol,
                    long_balance_change=None,
                    short_balance=shrt_vol,
                    short_balance_change=None,
                    sl_ratio=sl_ratio,
                )
            )
        logger.info("J-Quants: 全銘柄信用残高 %d 件を一括取得 (%s〜%s)", len(results), start, end)
        return results

    def fetch_dividends(self, code: str) -> list[MarketDividendData]:
        """配当・分配金履歴を取得（Premium プランのみ）。"""
        if not self.supports_dividend_fetch():
            return []
        jquants_code = code if len(code) == 5 else f"{code}0"
        try:
            df = self._call_with_backoff(self._client.get_fin_dividend, code=jquants_code)
        except Exception as e:
            logger.warning("J-Quants: %s の配当データ取得に失敗: %s", code, e)
            return []
        if df is None or df.empty:
            return []

        results: list[MarketDividendData] = []
        for _, row in df.iterrows():
            ex_date_str = str(row.get("ExDate", ""))[:10]
            div_val = row.get("DivAmt")
            if not ex_date_str or ex_date_str == "nan" or div_val is None:
                continue
            amount = _to_decimal_or_none(div_val)
            if amount is None or amount <= 0:
                continue
            try:
                ex_date = date.fromisoformat(ex_date_str)
            except ValueError:
                continue
            record_str = str(row.get("RecordDate", ""))[:10]
            payable_str = str(row.get("PayableDate", ""))[:10]
            results.append(
                MarketDividendData(
                    code=code,
                    ex_dividend_date=ex_date,
                    dividends_per_share=amount,
                    record_date=date.fromisoformat(record_str) if record_str and record_str != "nan" else None,
                    payable_date=date.fromisoformat(payable_str) if payable_str and payable_str != "nan" else None,
                )
            )
        logger.info("J-Quants: %s の配当データ %d 件を取得", code, len(results))
        return results


# ============================================================
# ヘルパー関数
# ============================================================


def _to_decimal(value: object) -> Decimal:
    """値をDecimalに変換。"""
    if value is None:
        return Decimal("0")
    s = str(value).strip()
    if s in ("", "nan", "-", "None"):
        return Decimal("0")
    return Decimal(s)


def _to_decimal_or_none(value: object) -> Decimal | None:
    """値をDecimalに変換。無効値はNone。"""
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "nan", "-", "None"):
        return None
    return Decimal(s)


def _to_int_or_none(value: object) -> int | None:
    """値をintに変換。無効値はNone。"""
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "nan", "-", "None"):
        return None
    return int(float(s))


def _to_bool_flag(value: object) -> bool:
    """J-Quants の UL/LL フラグ ('0' / '1' / 1 / 0) を bool に変換。

    NaN・None・空文字・"0" は False、それ以外で truthy なら True。
    """
    if value is None:
        return False
    s = str(value).strip()
    return s not in ("", "nan", "0", "None", "False")


def _to_adj_factor(value: object) -> Decimal:
    """AdjFactor 値を Decimal に変換。NaN・ゼロ・無効値は 1 として扱う。

    _to_decimal は NaN を 0 に変換するが、adj_factor=0 が保存されると
    effective_bps = bps × 0 = 0 となり calculable=False になるバグを防ぐ。
    """
    result = _to_decimal_or_none(value)
    if result is None or result <= 0:
        return Decimal("1")
    return result


def _derive_eps(row: Any) -> Decimal | None:
    """EPS を row から取得。null/nan の場合は NP / AvgSh で代替計算。

    J-Quants の `EPS` フィールドが未提供の場合（IFRS 採用企業等）、
    当期純利益（NP）と加重平均株式数（AvgSh）から算出する。
    """
    eps_raw = row.get("EPS")
    if eps_raw is not None and str(eps_raw).strip() not in ("", "nan", "-", "None"):
        return _to_decimal_or_none(eps_raw)
    # フォールバック: NP / AvgSh
    np_raw = row.get("NP")
    avg_sh_raw = row.get("AvgSh")
    if (
        np_raw is not None
        and str(np_raw).strip() not in ("", "nan", "-", "None")
        and avg_sh_raw is not None
        and str(avg_sh_raw).strip() not in ("", "nan", "-", "None", "0")
    ):
        try:
            return Decimal(str(np_raw)) / Decimal(str(avg_sh_raw))
        except Exception:
            pass
    return None


def _derive_feps(row: Any) -> Decimal | None:
    """会社予想EPS を取得。FEPS が null/nan の場合は FNP / AvgSh で代替計算。

    J-Quants の `FEPS` フィールドが未提供（IFRS 採用企業等）の場合、
    会社予想当期純利益（FNP）と加重平均株式数（AvgSh）から算出する。
    """
    feps_raw = row.get("FEPS")
    if feps_raw is not None and str(feps_raw).strip() not in ("", "nan", "-", "None"):
        return _to_decimal_or_none(feps_raw)
    # フォールバック: FNP / AvgSh
    fnp_raw = row.get("FNP")
    avg_sh_raw = row.get("AvgSh")
    if (
        fnp_raw is not None
        and str(fnp_raw).strip() not in ("", "nan", "-", "None")
        and avg_sh_raw is not None
        and str(avg_sh_raw).strip() not in ("", "nan", "-", "None", "0")
    ):
        try:
            return Decimal(str(fnp_raw)) / Decimal(str(avg_sh_raw))
        except Exception:
            pass
    return None


def _to_int_millions_or_none(value: object) -> int | None:
    """値を百万円単位のintに変換（J-Quantsは円単位）。"""
    raw = _to_int_or_none(value)
    if raw is None:
        return None
    return raw // 1_000_000


def _detect_instrument_type(name: str, market: str) -> str:
    """銘柄名と市場区分から instrument_type を判定。

    J-Quants では ETF・REIT ともに market='その他' となるため名前で区別する。
    「投資法人」を含む名称は J-REIT、それ以外は ETF・ETN とみなす。
    """
    if market not in ("その他",):
        return "stock"
    if "投資法人" in name:
        return "reit"
    return "etf"
