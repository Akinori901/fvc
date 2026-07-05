"""USD→JPY 換算サービス。

ポートフォリオ評価で米株（market_type='US'）の価格を JPY に変換するために使う。

ルール:
- 過去日: ``t_fx_rates`` (FxRate モデル) を引く。指定日のレートが無ければ「指定日以前の最新日」のレートで前方補完。
- 当日: DB に当日分が無ければ yfinance から最新値を 1 回だけ取得し、メモリにキャッシュ。
- yfinance 取得が失敗した場合は、DB の最新日レートにフォールバック。

最終的にどのレートも取得できなかった場合は ``None`` を返す。呼び出し側は
「換算不能 = その米株は集計から除外」として扱う想定。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

_PAIR = "USDJPY"


class FxConversionService:
    """指定日の USD/JPY を返す。インスタンスごとにキャッシュを持つ（1 リクエスト内で再利用）。"""

    def __init__(self) -> None:
        self._cache: dict[str, Decimal] = {}
        self._db_rates: dict[str, Decimal] | None = None
        self._db_latest_date: datetime.date | None = None
        self._realtime_rate: Decimal | None = None
        self._realtime_fetched = False

    def get_rate(self, target_date: datetime.date | str) -> Decimal | None:
        """指定日の USD/JPY を返す。前方補完あり。"""
        date_str = target_date if isinstance(target_date, str) else str(target_date)
        if date_str in self._cache:
            return self._cache[date_str]

        rate = self._resolve(date_str)
        if rate is not None:
            self._cache[date_str] = rate
        return rate

    def prefetch(self, dates: Iterable[datetime.date | str]) -> None:
        """指定日付群を一括で解決し、キャッシュに詰める。"""
        self._ensure_db_loaded()
        for d in dates:
            self.get_rate(d)

    # ── 内部 ──

    def _resolve(self, date_str: str) -> Decimal | None:
        self._ensure_db_loaded()
        assert self._db_rates is not None  # noqa: S101

        # 1) DB から日付指定 or 前方補完
        if date_str in self._db_rates:
            return self._db_rates[date_str]
        earlier = [d for d in self._db_rates if d <= date_str]
        if earlier:
            return self._db_rates[max(earlier)]

        # 2) DB に何も無い、または target が DB の最古より古い場合のフォールバック
        rt = self._fetch_realtime()
        if rt is not None:
            return rt

        # 3) 最終フォールバック: DB の最古値（あれば）
        if self._db_rates:
            oldest_date = min(self._db_rates)
            return self._db_rates[oldest_date]
        return None

    def _ensure_db_loaded(self) -> None:
        if self._db_rates is not None:
            return
        from apps.fx.infrastructure.models import FxRate

        rates: dict[str, Decimal] = {}
        latest_date: datetime.date | None = None
        for d, close in FxRate.objects.filter(pair=_PAIR).values_list("date", "close_rate"):
            rates[str(d)] = Decimal(str(close))
            if latest_date is None or d > latest_date:
                latest_date = d
        self._db_rates = rates
        self._db_latest_date = latest_date

    def _fetch_realtime(self) -> Decimal | None:
        """yfinance から最新の USD/JPY を取得（1 リクエスト内で 1 回だけ）。"""
        if self._realtime_fetched:
            return self._realtime_rate
        self._realtime_fetched = True
        try:
            import yfinance as yf

            ticker = yf.Ticker("USDJPY=X")
            hist = ticker.history(period="5d", auto_adjust=False)
            if hist.empty:
                logger.warning("yfinance USDJPY=X returned empty")
                return None
            last_close = hist["Close"].iloc[-1]
            rate = Decimal(str(last_close))
            self._realtime_rate = rate
        except Exception:
            logger.exception("Failed to fetch realtime USDJPY rate")
            return None
        else:
            return rate
