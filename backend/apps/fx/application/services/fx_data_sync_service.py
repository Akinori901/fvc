"""FXデータ同期サービス。

yfinance から USD/JPY レート、FRED から金利データを取得し DB に保存する。
PPP は Phase 1 ではハードコード値を使用。
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from ...domain.entities import FxRateEntity, MacroIndicatorEntity

if TYPE_CHECKING:
    from ...domain.repositories import FxRateRepository, InterestRateRepository, MacroIndicatorRepository
    from .fred_client_service import FredClientService

logger = logging.getLogger(__name__)

# PPP ハードコード値（OECD 公表値, Phase 1）
_PPP_USDJPY: dict[int, Decimal] = {
    2020: Decimal("96.78"),
    2021: Decimal("96.56"),
    2022: Decimal("93.97"),
    2023: Decimal("91.53"),
    2024: Decimal("92.30"),
    2025: Decimal("93.00"),  # 推定値
}


class FxDataSyncService:
    """FX データ同期サービス"""

    def __init__(
        self,
        fx_rate_repo: FxRateRepository,
        interest_rate_repo: InterestRateRepository,
        macro_indicator_repo: MacroIndicatorRepository,
        fred_client: FredClientService,
    ) -> None:
        self._fx_rate_repo = fx_rate_repo
        self._interest_rate_repo = interest_rate_repo
        self._macro_indicator_repo = macro_indicator_repo
        self._fred_client = fred_client

    def sync_fx_rates(self, *, full: bool = False) -> int:
        """yfinance から USD/JPY 日次レートを同期。"""
        import yfinance as yf

        if full:
            start_date = date(2020, 1, 1)
        else:
            latest = self._fx_rate_repo.find_latest_date(pair="USDJPY")
            start_date = latest - timedelta(days=5) if latest else date(2020, 1, 1)

        ticker = yf.Ticker("USDJPY=X")
        hist = ticker.history(start=start_date.isoformat(), auto_adjust=False)

        if hist.empty:
            logger.warning("yfinance: No data returned for USDJPY=X")
            return 0

        entities: list[FxRateEntity] = []
        for idx, row in hist.iterrows():
            try:
                close = Decimal(str(row["Close"]))
            except (InvalidOperation, KeyError):
                continue
            entities.append(
                FxRateEntity(
                    date=idx.date(),
                    pair="USDJPY",
                    close_rate=close,
                )
            )

        saved = self._fx_rate_repo.bulk_save(entities)
        logger.info("FX rates synced: %d saved (of %d fetched)", saved, len(entities))
        return saved

    def sync_interest_rates(self, *, full: bool = False) -> dict[str, int]:
        """FRED から US/JP 10Y 金利を同期。"""
        from .fred_client_service import SERIES_JP_10Y, SERIES_US_10Y

        results: dict[str, int] = {}

        for series_id, country in [(SERIES_US_10Y, "US"), (SERIES_JP_10Y, "JP")]:
            start_date: date | None = None
            if not full:
                latest = self._interest_rate_repo.find_latest_date(country, "10Y")
                if latest:
                    start_date = latest - timedelta(days=5)

            entities = self._fred_client.fetch_interest_rates(
                series_id,
                country,
                start_date=start_date,
            )
            saved = self._interest_rate_repo.bulk_save(entities)
            results[f"{country}_10Y"] = saved
            logger.info("Interest rates %s: %d saved", country, saved)

        return results

    def sync_ppp(self) -> int:
        """PPP ハードコード値を DB に保存。"""
        count = 0
        for year, value in _PPP_USDJPY.items():
            entity = MacroIndicatorEntity(
                indicator_type="PPP_USDJPY",
                value=value,
                year=year,
                source="OECD",
            )
            self._macro_indicator_repo.save(entity)
            count += 1
        logger.info("PPP data: %d years saved", count)
        return count

    def sync_all(self, *, full: bool = False) -> dict[str, object]:
        """全データソースを同期。"""
        fx_count = self.sync_fx_rates(full=full)
        rate_counts = self.sync_interest_rates(full=full)
        ppp_count = self.sync_ppp()
        return {
            "fx_rates": fx_count,
            **rate_counts,
            "ppp": ppp_count,
        }
