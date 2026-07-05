"""保有銘柄一覧ツール UseCase。

各口座の最新スナップショットを集計し、保有内容を返す。
動的株価による再評価結果は DynamicPortfolioValuationService を流用。
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.portfolios.application.services.dynamic_valuation_service import (
        DynamicPortfolioValuationService,
    )
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        FamilyMemberRepository,
        PortfolioAccountRepository,
    )


class GetMyHoldingsToolUseCase:
    """保有銘柄一覧（要 user_id）。"""

    def __init__(
        self,
        account_repo: PortfolioAccountRepository,
        snapshot_repo: AccountSnapshotRepository,
        member_repo: FamilyMemberRepository,
        valuation_service: DynamicPortfolioValuationService,
    ) -> None:
        self._account_repo = account_repo
        self._snapshot_repo = snapshot_repo
        self._member_repo = member_repo
        self._valuation_service = valuation_service

    def execute(self, *, user_id: int) -> dict[str, Any]:
        from apps.portfolios.application.services.dynamic_valuation_service import (
            DynamicValuationInput,
        )

        members = self._member_repo.find_by_user(user_id)
        accounts = self._account_repo.find_by_user(user_id)
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)

        member_name_by_id = {m.id: m.name for m in members if m.id is not None}
        account_meta_by_id = {a.id: a for a in accounts if a.id is not None}

        valuation = self._valuation_service.evaluate(
            DynamicValuationInput(
                accounts=accounts,
                snapshots=snapshots,
                as_of_date=datetime.date.today(),
            )
        )

        # holdings を集約
        holdings: list[dict[str, Any]] = []
        for snap in snapshots:
            account = account_meta_by_id.get(snap.account_id)
            account_label = account.nickname or account.institution if account else ""
            family_member_id = account.family_member_id if account else None
            member_name = member_name_by_id.get(family_member_id) if family_member_id is not None else None

            for h in snap.holdings:
                holdings.append(
                    {
                        "account_id": snap.account_id,
                        "account_label": account_label,
                        "asset_class": account.asset_class if account else None,
                        "trading_type": account.trading_type if account else None,
                        "family_member": member_name,
                        "stock_code": h.ticker_code or None,
                        "stock_id": h.stock_id,
                        "name": h.asset_name,
                        "asset_type": h.asset_type,
                        "quantity": _decimal_or_none(h.quantity),
                        "unit_price": _decimal_or_none(h.unit_price),
                        "snapshot_value_jpy": _decimal_or_none(h.value_jpy),
                        "cost_jpy": _decimal_or_none(h.cost_jpy),
                    }
                )

        return {
            "total_value": _decimal_or_none(valuation.total_value),
            "stock_total": _decimal_or_none(valuation.stock_total),
            "non_stock_value": _decimal_or_none(valuation.non_stock_value),
            "by_asset_class": {k: str(v) for k, v in valuation.by_asset_class.items()},
            "holdings": holdings,
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
