"""保有・ウォッチ銘柄の集約アラート取得ツール UseCase。

6 種類のアラートを保有銘柄 + ウォッチ銘柄に対して算出する:
- stop_high_today        : t_daily_movers.is_limit_up=True
- stop_low_today         : t_daily_movers.is_limit_down=True
- earnings_within_3d     : 決算予定が 5 暦日以内（3 営業日近似）
- margin_expiry_within_30d : 信用建玉の期限が 30 日以内
- risk_tag_high_severity : 銘柄の risk_tag に severity=high がある
- near_52w_high_breakout : |distance_from_52w_high| ≤ 2%
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from apps.mcp.domain.stock_tags import compute_risk_tags

if TYPE_CHECKING:
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        PortfolioAccountRepository,
        WatchlistRepository,
    )
    from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
    from apps.stocks.domain.repositories import (
        DailyMoversRepository,
        PriceRepository,
        StockRepository,
    )


logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
_EARNINGS_DAYS_AHEAD = 5  # 3 営業日 ≒ 5 暦日
_EXPIRY_WARNING_DAYS = 30
_NEAR_52W_HIGH_TOLERANCE = Decimal("0.02")
_DEFAULT_GROWTH_RATE = Decimal("0.02")


@dataclass(frozen=True)
class _AlertCandidate:
    code: str
    name: str
    alert_type: str
    severity: str
    detail: str
    source: str  # "holdings" / "watchlist"


class GetMyHoldingsAlertsToolUseCase:
    """保有 + ウォッチ銘柄の集約アラートを返す。"""

    def __init__(
        self,
        snapshot_repo: AccountSnapshotRepository,
        account_repo: PortfolioAccountRepository,
        watchlist_repo: WatchlistRepository,
        stock_repo: StockRepository,
        price_repo: PriceRepository,
        movers_repo: DailyMoversRepository,
        screening_usecase: ScreeningUseCase,
        earnings_calendar_tool_usecase: Any,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._account_repo = account_repo
        self._watchlist_repo = watchlist_repo
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._movers_repo = movers_repo
        self._screening_usecase = screening_usecase
        self._earnings_calendar_tool_usecase = earnings_calendar_tool_usecase

    def execute(self, *, user_id: int, severity_min: str = "low") -> dict[str, Any]:
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        accounts = {a.id: a for a in self._account_repo.find_by_user(user_id) if a.id is not None}
        watchlist = self._watchlist_repo.find_by_user(user_id)

        holdings_stock_ids: set[int] = set()
        for snap in snapshots:
            for h in snap.holdings:
                if h.stock_id is not None:
                    holdings_stock_ids.add(h.stock_id)
        watchlist_stock_ids: set[int] = {item.stock_id for item in watchlist if item.stock_id is not None}

        all_stock_ids = holdings_stock_ids | watchlist_stock_ids
        if not all_stock_ids:
            return {
                "as_of": datetime.date.today().isoformat(),
                "alerts_count": 0,
                "alerts": [],
            }

        # 銘柄メタを一括取得
        stock_meta: dict[int, tuple[str, str]] = {}
        codes_to_stock_id: dict[str, int] = {}
        for sid in all_stock_ids:
            stock = self._stock_repo.find_by_id(sid)
            if stock is not None:
                stock_meta[sid] = (stock.code, stock.name)
                codes_to_stock_id[stock.code] = sid

        today = datetime.date.today()
        candidates: list[_AlertCandidate] = []

        # 1-2. ストップ高/安
        candidates.extend(self._check_limit_hits(all_stock_ids, stock_meta, holdings_stock_ids))

        # 3. 決算 3 営業日以内
        candidates.extend(self._check_earnings_alerts(codes_to_stock_id, holdings_stock_ids, stock_meta))

        # 4. 信用建玉の期限
        candidates.extend(self._check_margin_expiry(snapshots, accounts, stock_meta, today))

        # 5. リスクタグ (severity=high)
        candidates.extend(self._check_risk_tags(all_stock_ids, stock_meta, holdings_stock_ids))

        # 6. 52w 高値ブレイク
        candidates.extend(self._check_52w_breakout(all_stock_ids, stock_meta, holdings_stock_ids))

        # severity_min フィルタ
        min_level = _SEVERITY_ORDER.get(severity_min, 0)
        filtered = [c for c in candidates if _SEVERITY_ORDER.get(c.severity, 0) >= min_level]

        return {
            "as_of": today.isoformat(),
            "alerts_count": len(filtered),
            "alerts": [_to_dto(c) for c in filtered],
        }

    # ────── 個別チェック ──────

    def _check_limit_hits(
        self,
        stock_ids: set[int],
        stock_meta: dict[int, tuple[str, str]],
        holdings_stock_ids: set[int],
    ) -> list[_AlertCandidate]:
        latest_date = self._movers_repo.find_latest_date()
        if latest_date is None:
            return []
        movers = self._movers_repo.find_by_date_and_stock_ids(latest_date, sorted(stock_ids))
        result: list[_AlertCandidate] = []
        for m in movers:
            code, name = stock_meta.get(m.stock_id, ("", ""))
            source = "holdings" if m.stock_id in holdings_stock_ids else "watchlist"
            if m.is_limit_up:
                result.append(
                    _AlertCandidate(
                        code=code,
                        name=name,
                        alert_type="stop_high_today",
                        severity="high",
                        detail=f"本日ストップ高（前日比 {m.change_pct or '?'}%）",
                        source=source,
                    )
                )
            if m.is_limit_down:
                result.append(
                    _AlertCandidate(
                        code=code,
                        name=name,
                        alert_type="stop_low_today",
                        severity="high",
                        detail=f"本日ストップ安（前日比 {m.change_pct or '?'}%）",
                        source=source,
                    )
                )
        return result

    def _check_earnings_alerts(
        self,
        codes_to_stock_id: dict[str, int],
        holdings_stock_ids: set[int],
        stock_meta: dict[int, tuple[str, str]],
    ) -> list[_AlertCandidate]:
        try:
            result = self._earnings_calendar_tool_usecase.execute(
                codes=list(codes_to_stock_id.keys()),
                days_ahead=_EARNINGS_DAYS_AHEAD,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("earnings_calendar 取得失敗: %s", exc)
            return []
        if not result.get("available", False):
            return []
        events = result.get("events", [])
        candidates: list[_AlertCandidate] = []
        for event in events:
            code = event.get("code")
            if not code or code not in codes_to_stock_id:
                continue
            sid = codes_to_stock_id[code]
            _, name = stock_meta.get(sid, ("", ""))
            source = "holdings" if sid in holdings_stock_ids else "watchlist"
            ann_date = event.get("announcement_date")
            candidates.append(
                _AlertCandidate(
                    code=code,
                    name=name,
                    alert_type="earnings_within_3d",
                    severity="medium",
                    detail=f"決算予定: {ann_date}（{_EARNINGS_DAYS_AHEAD} 暦日以内）",
                    source=source,
                )
            )
        return candidates

    def _check_margin_expiry(
        self,
        snapshots: list[Any],
        accounts: dict[int, Any],
        stock_meta: dict[int, tuple[str, str]],
        today: datetime.date,
    ) -> list[_AlertCandidate]:
        from apps.portfolios.application.services.margin_calculator_service import (
            MarginPositionInput,
            calculate,
        )

        candidates: list[_AlertCandidate] = []
        for snap in snapshots:
            account = accounts.get(snap.account_id)
            if account is None or account.trading_type != "margin":
                continue
            snapshot_date = datetime.date.fromisoformat(snap.snapshot_date)
            for h in snap.holdings:
                if h.stock_id is None:
                    continue
                calc = calculate(
                    MarginPositionInput(
                        built_date=h.built_date,
                        snapshot_date=snapshot_date,
                        credit_type=account.margin_credit_type,
                        interest_rate=account.margin_interest_rate,
                        cost_jpy=h.cost_jpy,
                        as_of=today,
                    )
                )
                if calc.days_to_expiry is None or calc.days_to_expiry > _EXPIRY_WARNING_DAYS:
                    continue
                code, name = stock_meta.get(h.stock_id, (h.ticker_code or "", h.asset_name))
                if calc.days_to_expiry < 0:
                    severity = "high"
                    detail = f"信用建玉が期限切れ ({calc.expiry_date})"
                else:
                    severity = "high" if calc.days_to_expiry <= 7 else "medium"
                    detail = f"信用建玉期限まで {calc.days_to_expiry} 日 ({calc.expiry_date})"
                candidates.append(
                    _AlertCandidate(
                        code=code,
                        name=name,
                        alert_type="margin_expiry_within_30d",
                        severity=severity,
                        detail=detail,
                        source="holdings",
                    )
                )
        return candidates

    def _check_risk_tags(
        self,
        stock_ids: set[int],
        stock_meta: dict[int, tuple[str, str]],
        holdings_stock_ids: set[int],
    ) -> list[_AlertCandidate]:
        candidates: list[_AlertCandidate] = []
        for sid in stock_ids:
            code, name = stock_meta.get(sid, ("", ""))
            if not code:
                continue
            try:
                results = self._screening_usecase.execute(
                    growth_rate=_DEFAULT_GROWTH_RATE,
                    code=code,
                    include_inactive=True,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("screening 失敗 (code=%s): %s", code, exc)
                continue
            if not results:
                continue
            tags = compute_risk_tags(results[0])
            high_tags = [t for t in tags if t.severity == "high"]
            if not high_tags:
                continue
            source = "holdings" if sid in holdings_stock_ids else "watchlist"
            for t in high_tags:
                candidates.append(
                    _AlertCandidate(
                        code=code,
                        name=name,
                        alert_type="risk_tag_high_severity",
                        severity="high",
                        detail=f"{t.tag}: {t.detail}",
                        source=source,
                    )
                )
        return candidates

    def _check_52w_breakout(
        self,
        stock_ids: set[int],
        stock_meta: dict[int, tuple[str, str]],
        holdings_stock_ids: set[int],
    ) -> list[_AlertCandidate]:
        candidates: list[_AlertCandidate] = []
        for sid in stock_ids:
            stock = self._stock_repo.find_by_id(sid)
            if stock is None or stock.latest_price is None:
                continue
            range_ = self._price_repo.find_52w_high_low(sid)
            if range_ is None:
                continue
            high, _ = range_
            if high <= 0:
                continue
            distance = (stock.latest_price - high) / high
            if abs(distance) > _NEAR_52W_HIGH_TOLERANCE:
                continue
            code, name = stock_meta.get(sid, (stock.code, stock.name))
            source = "holdings" if sid in holdings_stock_ids else "watchlist"
            candidates.append(
                _AlertCandidate(
                    code=code,
                    name=name,
                    alert_type="near_52w_high_breakout",
                    severity="medium",
                    detail=f"52w 高値 {high} 円から {distance:+.2%}（ブレイクアウト範囲）",
                    source=source,
                )
            )
        return candidates


def _to_dto(c: _AlertCandidate) -> dict[str, Any]:
    return {
        "code": c.code,
        "name": c.name,
        "alert_type": c.alert_type,
        "severity": c.severity,
        "detail": c.detail,
        "source": c.source,
    }
