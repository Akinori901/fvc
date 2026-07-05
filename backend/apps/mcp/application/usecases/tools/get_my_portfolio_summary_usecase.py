"""ポートフォリオサマリ取得ツール UseCase。

DynamicPortfolioValuationService.evaluate() の集計結果を MCP DTO に整形する。
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.portfolios.application.services.dynamic_valuation_service import (
        DynamicPortfolioValuationService,
    )
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        FamilyMemberRepository,
        PortfolioAccountRepository,
    )


class GetMyPortfolioSummaryToolUseCase:
    """ポートフォリオ全体の集計を返す（要 user_id）。

    含む情報:
    - total_value / total_cost / unrealized_pnl / unrealized_pnl_pct
    - by_asset_class
    - by_account（口座単位の評価額・原価・損益）
    - by_member（家族メンバー単位の評価額）
    """

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
        cost_by_account: dict[int, Decimal] = {}
        for snap in snapshots:
            if snap.total_cost_jpy is not None:
                cost_by_account[snap.account_id] = (
                    cost_by_account.get(snap.account_id, Decimal(0)) + snap.total_cost_jpy
                )

        valuation = self._valuation_service.evaluate(
            DynamicValuationInput(
                accounts=accounts,
                snapshots=snapshots,
                as_of_date=datetime.date.today(),
            )
        )

        total_cost = sum(cost_by_account.values(), Decimal(0))
        unrealized_pnl = valuation.total_value - total_cost if total_cost > 0 else None
        unrealized_pnl_pct = (
            (unrealized_pnl / total_cost * Decimal(100)) if unrealized_pnl is not None and total_cost > 0 else None
        )

        by_account: list[dict[str, Any]] = []
        for acc_id, value in valuation.by_account.items():
            acc = account_meta_by_id.get(acc_id)
            cost = cost_by_account.get(acc_id)
            pnl = (value - cost) if cost is not None else None
            by_account.append(
                {
                    "account_id": acc_id,
                    "label": (acc.nickname or acc.institution) if acc else "",
                    "institution": acc.institution if acc else "",
                    "asset_class": acc.asset_class if acc else None,
                    "trading_type": acc.trading_type if acc else None,
                    "family_member": _resolve_member_name(acc, member_name_by_id),
                    "value": _decimal_or_none(value),
                    "cost": _decimal_or_none(cost),
                    "pnl": _decimal_or_none(pnl),
                }
            )

        by_member: list[dict[str, Any]] = [
            {
                "member_id": m_id,
                "member_name": member_name_by_id.get(m_id, ""),
                "value": _decimal_or_none(value),
            }
            for m_id, value in valuation.by_member.items()
        ]

        return {
            "as_of": datetime.date.today().isoformat(),
            "total_value": _decimal_or_none(valuation.total_value),
            "total_cost": _decimal_or_none(total_cost) if total_cost > 0 else None,
            "unrealized_pnl": _decimal_or_none(unrealized_pnl),
            "unrealized_pnl_pct": _decimal_or_none(unrealized_pnl_pct),
            "stock_total": _decimal_or_none(valuation.stock_total),
            "non_stock_value": _decimal_or_none(valuation.non_stock_value),
            "by_asset_class": {k: str(v) for k, v in valuation.by_asset_class.items()},
            "by_account": by_account,
            "by_member": by_member,
            "day_change_pct": None,
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _resolve_member_name(account: Any, member_name_by_id: dict[int, str]) -> str | None:
    if account is None or account.family_member_id is None:
        return None
    return member_name_by_id.get(account.family_member_id)
