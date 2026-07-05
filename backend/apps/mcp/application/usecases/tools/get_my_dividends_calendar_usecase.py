"""保有銘柄の配当カレンダー取得ツール UseCase。

ユーザーの保有銘柄について、ex_dividend_date が今後 N ヶ月以内の配当予定と
保有数量から計算した受取予定額を返す。

データソースの制約:
- yfinance は ex_dividend_date と金額のみ → record_date / payable_date は空
- J-Quants Premium は record_date / payable_date まで取り込み
- 同期対象は標準で ETF/REIT のみ。普通株は dividend_sync の拡張が必要

データ充足が不足する場合は warnings に "data_may_be_incomplete" を立てる。
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.portfolios.domain.repositories import AccountSnapshotRepository
    from apps.stocks.domain.repositories import DividendRepository, StockRepository


_DEFAULT_MONTHS_AHEAD = 3
_MONTH_DAYS = 31  # 月数 → 日数の近似（厳密な月末計算は不要）


class GetMyDividendsCalendarToolUseCase:
    """保有銘柄の今後 N ヶ月の配当予定と受取予定額を返す（要 user_id）。"""

    def __init__(
        self,
        snapshot_repo: AccountSnapshotRepository,
        stock_repo: StockRepository,
        dividend_repo: DividendRepository,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._stock_repo = stock_repo
        self._dividend_repo = dividend_repo

    def execute(
        self,
        *,
        user_id: int,
        months_ahead: int = _DEFAULT_MONTHS_AHEAD,
    ) -> dict[str, Any]:
        # 保有 stock_id × 数量を集約（複数口座は合算）
        quantity_by_stock: dict[int, Decimal] = {}
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        for snap in snapshots:
            for h in snap.holdings:
                if h.stock_id is None or h.quantity is None or h.quantity <= 0:
                    continue
                quantity_by_stock[h.stock_id] = quantity_by_stock.get(h.stock_id, Decimal(0)) + h.quantity

        if not quantity_by_stock:
            return _empty_response(months_ahead)

        # 配当予定を一括取得
        today = datetime.date.today()
        to_date = today + datetime.timedelta(days=months_ahead * _MONTH_DAYS)
        dividends = self._dividend_repo.find_upcoming_by_stock_ids(
            sorted(quantity_by_stock.keys()),
            from_date=today,
            to_date=to_date,
        )

        # 銘柄メタを一括取得
        stock_meta: dict[int, tuple[str, str]] = {}
        for sid in {d.stock_id for d in dividends}:
            stock = self._stock_repo.find_by_id(sid)
            if stock is not None:
                stock_meta[sid] = (stock.code, stock.name)

        upcoming: list[dict[str, Any]] = []
        total_expected = Decimal(0)
        for d in dividends:
            qty = quantity_by_stock.get(d.stock_id)
            if qty is None:
                continue
            expected = (d.dividends_per_share * qty).quantize(Decimal("1"))
            total_expected += expected
            code, name = stock_meta.get(d.stock_id, ("", ""))
            upcoming.append(
                {
                    "code": code,
                    "name": name,
                    "stock_id": d.stock_id,
                    "ex_dividend_date": d.ex_dividend_date.isoformat(),
                    "record_date": d.record_date.isoformat() if d.record_date else None,
                    "payable_date": d.payable_date.isoformat() if d.payable_date else None,
                    "dividend_per_share": str(d.dividends_per_share),
                    "quantity": str(qty),
                    "expected_amount": str(expected),
                    "source": d.source,
                }
            )

        warnings: list[str] = []
        if not upcoming and quantity_by_stock:
            warnings.append("data_may_be_incomplete")

        return {
            "as_of": today.isoformat(),
            "months_ahead": months_ahead,
            "currency": "JPY",
            "upcoming": upcoming,
            "total_expected_amount": str(total_expected),
            "warnings": warnings,
        }


def _empty_response(months_ahead: int) -> dict[str, Any]:
    return {
        "as_of": datetime.date.today().isoformat(),
        "months_ahead": months_ahead,
        "currency": "JPY",
        "upcoming": [],
        "total_expected_amount": "0",
        "warnings": [],
    }
