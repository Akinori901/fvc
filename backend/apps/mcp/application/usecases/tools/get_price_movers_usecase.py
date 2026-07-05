"""急騰急落ランキング取得ツール UseCase。

t_daily_movers から指定日（デフォルト最新）の集計を取得し、
direction / scope / threshold / volume_ratio フィルタで絞り込んだ後、
change_pct 順に gainers / losers をランキングして返す。

scope:
- "all"          : 全銘柄
- "my_watchlist" : ログイン中ユーザーのウォッチリスト銘柄に絞る (要 user_id)
- "my_holdings"  : ログイン中ユーザーの保有銘柄に絞る (要 user_id)
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime

    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        WatchlistRepository,
    )
    from apps.stocks.domain.entities import DailyMoversEntity
    from apps.stocks.domain.repositories import DailyMoversRepository, StockRepository


_DEFAULT_LIMIT = 20
_DEFAULT_THRESHOLD_PCT = Decimal("5.0")


class GetPriceMoversToolUseCase:
    """急騰急落ランキングを返す。"""

    def __init__(
        self,
        movers_repo: DailyMoversRepository,
        stock_repo: StockRepository,
        snapshot_repo: AccountSnapshotRepository,
        watchlist_repo: WatchlistRepository,
    ) -> None:
        self._movers_repo = movers_repo
        self._stock_repo = stock_repo
        self._snapshot_repo = snapshot_repo
        self._watchlist_repo = watchlist_repo

    def execute(
        self,
        *,
        direction: str = "both",
        scope: str = "all",
        threshold_pct: Decimal | None = None,
        min_volume_ratio: Decimal | None = None,
        include_limit_hits: bool = True,
        limit: int = _DEFAULT_LIMIT,
        target_date: datetime.date | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        if direction not in ("gainers", "losers", "both"):
            raise ValueError(f"direction must be one of gainers/losers/both: {direction}")
        if scope not in ("all", "my_watchlist", "my_holdings"):
            raise ValueError(f"scope must be one of all/my_watchlist/my_holdings: {scope}")
        if scope in ("my_watchlist", "my_holdings") and user_id is None:
            raise PermissionError(f"scope={scope} には user_id が必要です")

        threshold = threshold_pct if threshold_pct is not None else _DEFAULT_THRESHOLD_PCT

        # 日付決定
        resolved_date = target_date or self._movers_repo.find_latest_date()
        if resolved_date is None:
            return _empty_response(scope=scope, direction=direction)

        # universe フィルタ
        entries = self._fetch_entries(resolved_date, scope, user_id)

        # 閾値・出来高比・ストップフィルタ
        filtered = _apply_filters(
            entries,
            threshold=threshold,
            min_volume_ratio=min_volume_ratio,
            include_limit_hits=include_limit_hits,
        )

        # 銘柄名解決（stock_id → name/code）
        stock_meta = self._fetch_stock_meta({e.stock_id for e in filtered})

        gainers: list[dict[str, Any]] = []
        losers: list[dict[str, Any]] = []
        if direction in ("gainers", "both"):
            sorted_gainers = sorted(
                [e for e in filtered if e.change_pct is not None and e.change_pct > 0],
                key=lambda e: e.change_pct or Decimal("0"),
                reverse=True,
            )
            gainers = [_to_dto(e, stock_meta) for e in sorted_gainers[:limit]]
        if direction in ("losers", "both"):
            sorted_losers = sorted(
                [e for e in filtered if e.change_pct is not None and e.change_pct < 0],
                key=lambda e: e.change_pct or Decimal("0"),
            )
            losers = [_to_dto(e, stock_meta) for e in sorted_losers[:limit]]

        return {
            "as_of": resolved_date.isoformat(),
            "scope": scope,
            "direction": direction,
            "filters_applied": {
                "threshold_pct": str(threshold),
                "min_volume_ratio": _decimal_or_none(min_volume_ratio),
                "include_limit_hits": include_limit_hits,
                "limit": limit,
            },
            "gainers": gainers,
            "losers": losers,
        }

    def _fetch_entries(self, target_date: datetime.date, scope: str, user_id: int | None) -> list[DailyMoversEntity]:
        if scope == "all":
            return self._movers_repo.find_by_date(target_date)

        assert user_id is not None
        stock_ids: set[int] = set()
        if scope == "my_holdings":
            for snap in self._snapshot_repo.find_latest_by_user(user_id):
                for h in snap.holdings:
                    if h.stock_id is not None:
                        stock_ids.add(h.stock_id)
        elif scope == "my_watchlist":
            for item in self._watchlist_repo.find_by_user(user_id):
                if item.stock_id is not None:
                    stock_ids.add(item.stock_id)

        return self._movers_repo.find_by_date_and_stock_ids(target_date, sorted(stock_ids))

    def _fetch_stock_meta(self, stock_ids: set[int]) -> dict[int, tuple[str, str]]:
        """stock_id → (code, name) のマップを返す。"""
        result: dict[int, tuple[str, str]] = {}
        for sid in stock_ids:
            stock = self._stock_repo.find_by_id(sid)
            if stock is not None:
                result[sid] = (stock.code, stock.name)
        return result


def _apply_filters(
    entries: list[DailyMoversEntity],
    *,
    threshold: Decimal,
    min_volume_ratio: Decimal | None,
    include_limit_hits: bool,
) -> list[DailyMoversEntity]:
    result: list[DailyMoversEntity] = []
    for e in entries:
        is_limit_hit = e.is_limit_up or e.is_limit_down
        bypass_threshold = include_limit_hits and is_limit_hit

        if not bypass_threshold and (e.change_pct is None or abs(e.change_pct) < threshold):
            continue

        if min_volume_ratio is not None and (e.volume_ratio_20d is None or e.volume_ratio_20d < min_volume_ratio):
            continue

        result.append(e)
    return result


def _to_dto(entry: DailyMoversEntity, stock_meta: dict[int, tuple[str, str]]) -> dict[str, Any]:
    code, name = stock_meta.get(entry.stock_id, ("", ""))
    return {
        "code": code,
        "name": name,
        "close": _decimal_or_none(entry.close_price),
        "prev_close": _decimal_or_none(entry.prev_close),
        "change_pct": _decimal_or_none(entry.change_pct),
        "volume": entry.volume,
        "volume_ratio_20d": _decimal_or_none(entry.volume_ratio_20d),
        "is_limit_up": entry.is_limit_up,
        "is_limit_down": entry.is_limit_down,
    }


def _empty_response(*, scope: str, direction: str) -> dict[str, Any]:
    return {
        "as_of": None,
        "scope": scope,
        "direction": direction,
        "filters_applied": {},
        "gainers": [],
        "losers": [],
    }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
