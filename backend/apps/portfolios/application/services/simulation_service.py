from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.portfolios.domain.entities import AccountHoldingEntity, PortfolioAccountEntity
    from apps.stocks.domain.entities import FinancialEntity

_MAX_GROWTH_RATE = Decimal("0.30")  # 30%キャップ


@dataclass
class HoldingSimulation:
    asset_name: str
    ticker_code: str
    asset_type: str
    category: str
    current_value: Decimal
    growth_rate: Decimal
    growth_rate_source: str
    yearly_values: list[Decimal] = field(default_factory=list)


@dataclass
class SimulationResult:
    years: int
    holdings: list[HoldingSimulation]
    yearly_totals: list[Decimal] = field(default_factory=list)
    yearly_by_category: dict[str, list[Decimal]] = field(default_factory=dict)


def _compute_eps_cagr(financials: list[FinancialEntity]) -> Decimal | None:
    """全期間のEPSからCAGRを計算。fiscal_year DESC順を想定。"""
    valid = [f for f in financials if f.eps is not None and f.eps > 0]
    if len(valid) < 2:
        return None
    latest = valid[0]
    earliest = valid[-1]
    n_years = latest.fiscal_year - earliest.fiscal_year
    if n_years <= 0:
        return None
    ratio = latest.eps / earliest.eps  # type: ignore[operator]
    cagr = ratio ** (Decimal("1") / Decimal(str(n_years))) - Decimal("1")
    if cagr > _MAX_GROWTH_RATE:
        return _MAX_GROWTH_RATE
    return cagr


def _compute_yearly_values(current_value: Decimal, rate: Decimal, years: int) -> list[Decimal]:
    """year 0 ~ year N の評価額リストを返す。"""
    values: list[Decimal] = [current_value]
    val = current_value
    multiplier = Decimal("1") + rate
    for _ in range(years):
        val = val * multiplier
        values.append(val.quantize(Decimal("1")))
    return values


class SimulationService:
    """保有銘柄の将来シミュレーションを計算する。"""

    def simulate(
        self,
        holdings: list[tuple[AccountHoldingEntity, PortfolioAccountEntity]],
        financials_by_stock: dict[int, list[FinancialEntity]],
        years: int,
        fund_growth_rate: Decimal,
    ) -> SimulationResult:
        sims: list[HoldingSimulation] = []

        for holding, account in holdings:
            rate, source = self._determine_growth_rate(holding, account, financials_by_stock, fund_growth_rate)
            yearly = _compute_yearly_values(holding.value_jpy, rate, years)
            sims.append(
                HoldingSimulation(
                    asset_name=holding.asset_name,
                    ticker_code=holding.ticker_code,
                    asset_type=holding.asset_type,
                    category=account.asset_class,
                    current_value=holding.value_jpy,
                    growth_rate=rate,
                    growth_rate_source=source,
                    yearly_values=yearly,
                )
            )

        # 年次合計・カテゴリ別集計
        yearly_totals = [Decimal("0")] * (years + 1)
        cat_map: dict[str, list[Decimal]] = {}

        for sim in sims:
            if sim.category not in cat_map:
                cat_map[sim.category] = [Decimal("0")] * (years + 1)
            for i, val in enumerate(sim.yearly_values):
                yearly_totals[i] += val
                cat_map[sim.category][i] += val

        return SimulationResult(
            years=years,
            holdings=sims,
            yearly_totals=yearly_totals,
            yearly_by_category=cat_map,
        )

    def _determine_growth_rate(
        self,
        holding: AccountHoldingEntity,
        account: PortfolioAccountEntity,
        financials_by_stock: dict[int, list[FinancialEntity]],
        fund_growth_rate: Decimal,
    ) -> tuple[Decimal, str]:
        """成長率とそのソースを決定する。"""
        # 1. 個別株 — EPS CAGR
        if holding.stock_id and holding.stock_id in financials_by_stock:
            cagr = _compute_eps_cagr(financials_by_stock[holding.stock_id])
            if cagr is not None:
                return cagr, "eps_cagr"

        # 2. 投資信託 — スライダー値
        if holding.asset_type == "fund":
            return fund_growth_rate, "fund_slider"

        # 3. 口座設定の期待リターン率
        if account.expected_return_rate is not None:
            return account.expected_return_rate / Decimal("100"), "account_rate"

        # 4. フォールバック — 横ばい
        return Decimal("0"), "flat"
