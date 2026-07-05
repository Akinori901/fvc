"""FRED API クライアントサービス。

Federal Reserve Economic Data (FRED) から金利データを取得する。
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx

from ...domain.entities import InterestRateEntity
from ...domain.exceptions import FredApiError

logger = logging.getLogger(__name__)

_FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# FRED Series IDs
SERIES_US_10Y = "DGS10"  # US 10-Year Treasury (daily)
SERIES_JP_10Y = "IRLTLT01JPM156N"  # Japan 10-Year Government Bond (monthly)


class FredClientService:
    """FRED API クライアント"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch_series(
        self,
        series_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, str]]:
        """FRED series の observations を取得。

        Returns:
            [{"date": "2024-01-02", "value": "3.95"}, ...]
        """
        params: dict[str, str] = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
        }
        if start_date:
            params["observation_start"] = start_date.isoformat()
        if end_date:
            params["observation_end"] = end_date.isoformat()

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(_FRED_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise FredApiError(f"FRED API error for {series_id}: {e}") from e

        result: list[dict[str, str]] = data.get("observations", [])
        return result

    def fetch_interest_rates(
        self,
        series_id: str,
        country: str,
        rate_type: str = "10Y",
        *,
        start_date: date | None = None,
    ) -> list[InterestRateEntity]:
        """金利データを InterestRateEntity のリストとして取得。"""
        observations = self.fetch_series(series_id, start_date=start_date)
        entities: list[InterestRateEntity] = []

        for obs in observations:
            value_str = obs.get("value", "")
            if value_str == "." or not value_str:
                continue  # FRED uses "." for missing values
            try:
                rate = Decimal(value_str)
            except InvalidOperation:
                continue
            entities.append(
                InterestRateEntity(
                    date=date.fromisoformat(obs["date"]),
                    country=country,
                    rate_type=rate_type,
                    rate=rate,
                )
            )

        logger.info("FRED %s: fetched %d observations", series_id, len(entities))
        return entities
