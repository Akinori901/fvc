"""信用建玉一覧取得ツール UseCase。

ユーザーの全口座のうち trading_type='margin' のものを抽出し、
各 holding に対し margin_calculator_service で期限・累計金利・現引き必要資金を計算する。

cost_jpy / built_date / interest_rate が NULL の場合は計算可能な範囲だけ返し、
不足項目は null とする（グレースフル）。
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from apps.portfolios.application.services.margin_calculator_service import (
    MarginPositionInput,
    calculate,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.portfolios.application.services.dynamic_valuation_service import StockPriceSource
    from apps.portfolios.domain.entities import AccountSnapshotEntity, PortfolioAccountEntity
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        PortfolioAccountRepository,
    )


class GetMyMarginPositionsToolUseCase:
    """ログイン中ユーザーの信用建玉詳細を返す（要 user_id）。"""

    def __init__(
        self,
        account_repo: PortfolioAccountRepository,
        snapshot_repo: AccountSnapshotRepository,
        price_source: StockPriceSource,
    ) -> None:
        self._account_repo = account_repo
        self._snapshot_repo = snapshot_repo
        self._price_source = price_source

    def execute(self, *, user_id: int) -> dict[str, Any]:
        accounts = self._account_repo.find_by_user(user_id)
        margin_accounts: dict[int, PortfolioAccountEntity] = {
            a.id: a for a in accounts if a.id is not None and a.trading_type == "margin"
        }
        if not margin_accounts:
            return {"count": 0, "as_of": datetime.date.today().isoformat(), "positions": []}

        snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        margin_snapshots = [s for s in snapshots if s.account_id in margin_accounts]

        # 最新株価を一括取得
        stock_ids: set[int] = set()
        for snap in margin_snapshots:
            for h in snap.holdings:
                if h.stock_id is not None:
                    stock_ids.add(h.stock_id)
        latest_price_map = self._price_source.fetch_latest_prices(stock_ids) if stock_ids else {}

        today = datetime.date.today()
        positions: list[dict[str, Any]] = []
        for snap in margin_snapshots:
            account = margin_accounts[snap.account_id]
            snapshot_date = _parse_snapshot_date(snap)
            for h in snap.holdings:
                positions.append(
                    _build_position_dto(
                        account=account,
                        holding=h,
                        snapshot_date=snapshot_date,
                        latest_price=latest_price_map.get(h.stock_id) if h.stock_id else None,
                        today=today,
                    )
                )

        return {
            "count": len(positions),
            "as_of": today.isoformat(),
            "positions": positions,
        }


def _parse_snapshot_date(snap: AccountSnapshotEntity) -> datetime.date:
    return datetime.date.fromisoformat(snap.snapshot_date)


def _build_position_dto(
    *,
    account: PortfolioAccountEntity,
    holding: Any,
    snapshot_date: datetime.date,
    latest_price: Decimal | None,
    today: datetime.date,
) -> dict[str, Any]:
    calc = calculate(
        MarginPositionInput(
            built_date=holding.built_date,
            snapshot_date=snapshot_date,
            credit_type=account.margin_credit_type,
            interest_rate=account.margin_interest_rate,
            cost_jpy=holding.cost_jpy,
            as_of=today,
        )
    )
    qty = holding.quantity
    market_value = qty * latest_price if qty is not None and latest_price is not None else None
    unrealized_pnl = (
        (market_value - holding.cost_jpy) if market_value is not None and holding.cost_jpy is not None else None
    )

    return {
        "stock_code": holding.ticker_code or None,
        "stock_id": holding.stock_id,
        "name": holding.asset_name,
        "account_id": account.id,
        "account_label": account.nickname or account.institution,
        "credit_type": account.margin_credit_type,
        "credit_type_display": _credit_type_display(account.margin_credit_type),
        "quantity": _decimal_or_none(qty),
        "built_date": holding.built_date.isoformat() if holding.built_date else None,
        "effective_built_date": calc.effective_built_date.isoformat(),
        "expiry_date": calc.expiry_date.isoformat() if calc.expiry_date else None,
        "days_to_expiry": calc.days_to_expiry,
        "days_held": calc.days_held,
        "build_price": _decimal_or_none(holding.unit_price),
        "current_price": _decimal_or_none(latest_price),
        "interest_rate": _decimal_or_none(account.margin_interest_rate),
        "accrued_interest": _decimal_or_none(calc.accrued_interest),
        "cost_jpy": _decimal_or_none(holding.cost_jpy),
        "genbiki_cash_required": _decimal_or_none(calc.genbiki_cash_required),
        "market_value": _decimal_or_none(market_value),
        "unrealized_pnl": _decimal_or_none(unrealized_pnl),
        "warning_tags": calc.warning_tags,
    }


def _credit_type_display(credit_type: str | None) -> str:
    labels = {
        "system_6m": "制度信用 (6ヶ月)",
        "general_6m": "一般信用 (6ヶ月)",
        "general_unlimited": "一般信用 (無期限)",
    }
    return labels.get(credit_type or "", "")


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
