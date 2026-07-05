from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.portfolios.application.services.simulation_service import SimulationResult, SimulationService
    from apps.portfolios.domain.entities import AccountHoldingEntity, PortfolioAccountEntity
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        FamilyMemberRepository,
        PortfolioAccountRepository,
    )
    from apps.stocks.domain.repositories import FinancialRepository


class PortfolioSimulationUseCase:
    """ポートフォリオ将来シミュレーション。"""

    def __init__(
        self,
        snapshot_repo: AccountSnapshotRepository,
        account_repo: PortfolioAccountRepository,
        member_repo: FamilyMemberRepository,
        financial_repo: FinancialRepository,
        simulation_service: SimulationService,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._account_repo = account_repo
        self._member_repo = member_repo
        self._financial_repo = financial_repo
        self._simulation_service = simulation_service

    def execute(
        self,
        user_id: int,
        years: int,
        view: str,
        fund_growth_rate: Decimal,
    ) -> SimulationResult:
        members = self._member_repo.find_by_user(user_id)
        accounts = self._account_repo.find_by_user(user_id)
        latest_snapshots = self._snapshot_repo.find_latest_by_user(user_id)

        # view モードでフィルタ
        self_member = next((m for m in members if m.role == "self"), None)
        if view == "individual":
            target_ids = {self_member.id} if self_member and self_member.id else set()
        else:
            target_ids = {m.id for m in members if m.include_in_family_total and m.id is not None}

        # 口座マップ
        account_map: dict[int, PortfolioAccountEntity] = {
            a.id: a for a in accounts if a.id is not None and a.family_member_id in target_ids
        }
        # スナップショットマップ
        snap_map = {s.account_id: s for s in latest_snapshots}

        # holdings と対応する account をペアで収集
        holdings_with_account: list[tuple[AccountHoldingEntity, PortfolioAccountEntity]] = []
        stock_ids: set[int] = set()

        for acc_id, account in account_map.items():
            snap = snap_map.get(acc_id)
            if not snap:
                continue
            for holding in snap.holdings:
                holdings_with_account.append((holding, account))
                if holding.stock_id:
                    stock_ids.add(holding.stock_id)

        # 財務データ一括取得
        financials_by_stock = self._financial_repo.find_by_stock_ids(list(stock_ids))

        return self._simulation_service.simulate(
            holdings=holdings_with_account,
            financials_by_stock=financials_by_stock,
            years=years,
            fund_growth_rate=fund_growth_rate,
        )
