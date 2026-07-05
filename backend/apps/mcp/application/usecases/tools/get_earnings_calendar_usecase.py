"""決算カレンダーツール UseCase（J-Quants /equities/earnings-calendar）。"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import MarketDataProvider


class GetEarningsCalendarToolUseCase:
    """今後 N 日分の決算予定を返す。

    J-Quants `/equities/earnings-calendar` をラップ。
    """

    def __init__(self, jquants_provider_factory: Any) -> None:
        """jquants_provider_factory: 呼び出し時に MarketDataProvider を返すファクトリ関数。"""
        self._jquants_provider_factory = jquants_provider_factory

    def execute(self, *, codes: list[str] | None = None, days_ahead: int = 30) -> dict[str, Any]:
        provider = self._get_jquants_client()
        if provider is None:
            return {
                "available": False,
                "reason": "J-Quants が利用できない設定です（m_api_configs に provider='jquants' を登録してください）",
                "events": [],
            }

        # JQuantsClient は内部に jquantsapi.ClientV2 を持つので get_eq_earnings_cal を直接呼ぶ
        try:
            client = provider._client  # type: ignore[attr-defined]
            df = client.get_eq_earnings_cal()
        except Exception as exc:  # noqa: BLE001
            logger.warning("J-Quants earnings calendar fetch failed: %s", exc)
            return {
                "available": False,
                "reason": f"J-Quants API エラー: {exc}",
                "events": [],
            }

        if df is None or len(df) == 0:
            return {"available": True, "events": []}

        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days_ahead)
        events: list[dict[str, Any]] = []

        for _idx, row in df.iterrows():
            code = str(row.get("Code", "")).strip()
            if codes is not None and code not in codes:
                continue

            date_raw = row.get("Date") or row.get("AnnouncementDate")
            announcement_date = _parse_date(date_raw)
            if announcement_date is None:
                continue
            if announcement_date < today or announcement_date > end_date:
                continue

            events.append(
                {
                    "code": code,
                    "company_name": str(row.get("CompanyName", "") or ""),
                    "announcement_date": announcement_date.isoformat(),
                    "fiscal_year": str(row.get("FiscalYear", "") or "") or None,
                    "fiscal_quarter": str(row.get("FiscalQuarter", "") or "") or None,
                    "sector_name": str(row.get("SectorName", "") or "") or None,
                }
            )

        events.sort(key=lambda e: e["announcement_date"])
        return {"available": True, "events": events, "days_ahead": days_ahead}

    def _get_jquants_client(self) -> MarketDataProvider | None:
        try:
            provider: MarketDataProvider = self._jquants_provider_factory()
        except RuntimeError as exc:
            logger.info("J-Quants client unavailable: %s", exc)
            return None
        return provider


def _parse_date(value: Any) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None
