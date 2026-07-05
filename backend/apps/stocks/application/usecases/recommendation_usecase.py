"""ダッシュボード用の日本株おすすめ抽出ユースケース。

3カテゴリ各5件:
1. 長期保有 — 高配当・連続配当・割安・業績成長
2. デイトレ — 高ボラティリティ・高出来高
3. レンジ — 1年レンジ幅500円以上・ドリフト小・業績安定
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from apps.stocks.domain.dividend_metrics import compute_dividend_metrics
from apps.stocks.domain.growth_metrics import compute_growth_metrics
from apps.stocks.domain.technical_metrics import (
    compute_range_metrics_1y,
    compute_technical_metrics,
    compute_volatility_20d,
)
from apps.valuations.domain.entities import MARKET_COST_OF_CAPITAL, FairValueCalculation

if TYPE_CHECKING:
    from apps.stocks.domain.entities import DividendEntity, FinancialEntity, PriceEntity, StockEntity
    from apps.stocks.domain.repositories import (
        DividendRepository,
        FinancialRepository,
        PriceRepository,
        StockRepository,
    )

logger = logging.getLogger(__name__)

# screening と同じ非株式市場除外セット
_NON_EQUITY_MARKETS = frozenset({"その他", "TOKYO PRO MARKET"})

# 抽出基準のしきい値
# NOTE: 普通株の配当データは現状未取得（sync_dividends は ETF/REIT 専用）。
# 配当条件は将来 sync_dividends を普通株対応にした時点で有効化する。
_LONG_TERM_MIN_DIVIDEND_YIELD = Decimal("3.0")
_LONG_TERM_MIN_CONSECUTIVE_YEARS = 10
_LONG_TERM_MIN_EPS_CAGR_3Y = Decimal("0.03")  # 年率 3%以上の業績成長
_LONG_TERM_MAX_EPS_CAGR_3Y = Decimal("0.50")  # 50%超は赤字→黒字転換系の異常値除外
_LONG_TERM_MIN_DISCOUNT_RATE = Decimal("0.10")  # 適正株価より10%以上割安
_DAY_TRADE_MIN_PRICE = Decimal("100")
_DAY_TRADE_MIN_VOLATILITY = Decimal("2.0")  # 日次標準偏差 2.0%以上
_DAY_TRADE_LIQUIDITY_LEVELS = frozenset({"high", "medium"})
_RANGE_MIN_WIDTH = Decimal("500")  # レンジ幅 500円以上
_RANGE_MAX_DRIFT_PCT = Decimal("0.15")  # ±15% 以内
_RANGE_MAX_EPS_CAGR_PCT = Decimal("10")  # ±10% 以内（急成長/急減速ではない）

_TOP_N = 5


@dataclass
class RecommendedStock:
    code: str
    name: str
    latest_price: Decimal | None
    metrics: dict[str, str]
    stock_id: int = 0
    score: Decimal = Decimal("0")


@dataclass
class RecommendationsDTO:
    long_term: list[RecommendedStock] = field(default_factory=list)
    day_trade: list[RecommendedStock] = field(default_factory=list)
    range_bound: list[RecommendedStock] = field(default_factory=list)


class RecommendationUseCase:
    """日本株おすすめ抽出。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        price_repo: PriceRepository,
        dividend_repo: DividendRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._price_repo = price_repo
        self._dividend_repo = dividend_repo

    def execute(self) -> RecommendationsDTO:
        # 日本株の普通株のみ抽出
        stocks = self._stock_repo.find_by_market_type("JP", active_only=True)
        stocks = [
            s
            for s in stocks
            if s.id is not None
            and s.market not in _NON_EQUITY_MARKETS
            and getattr(s, "instrument_type", "stock") == "stock"
        ]

        # 一括取得
        all_financials = self._financial_repo.find_all_latest()
        all_recent_financials = self._financial_repo.find_all_recent(limit=4)
        all_52w = self._price_repo.find_all_52w_high_low() if self._price_repo else {}
        # レンジ計算用に 252日（約1年） + 20日ボラ計算用にも兼ねる
        all_long_prices = self._price_repo.find_all_recent_prices(limit=252) if self._price_repo else {}

        # 配当データ
        stock_ids = [s.id for s in stocks if s.id is not None]

        all_annual_totals: dict[int, Decimal] = {}
        all_dividends: dict[int, list[DividendEntity]] = {}
        if self._dividend_repo and stock_ids:
            try:
                all_annual_totals = self._dividend_repo.find_all_annual_totals(stock_ids)
                all_dividends = self._dividend_repo.find_all_by_stock_ids(stock_ids)
            except Exception:
                logger.warning("配当データの取得に失敗。フォールバック。", exc_info=True)

        # 各銘柄ごとにメトリクスを算出
        long_term_candidates: list[tuple[Decimal, RecommendedStock]] = []
        day_trade_candidates: list[tuple[Decimal, RecommendedStock]] = []
        range_candidates: list[tuple[Decimal, RecommendedStock]] = []

        cost_of_capital = MARKET_COST_OF_CAPITAL.get("JP", Decimal("0.10"))
        growth_rate = Decimal("0.02")  # 共通の想定成長率（screening と同じ）

        for stock in stocks:
            if stock.id is None or stock.latest_price is None:
                continue

            financial = all_financials.get(stock.id)
            recent_financials = all_recent_financials.get(stock.id, [])
            recent_prices = all_long_prices.get(stock.id, [])

            # ----- 長期保有候補 -----
            lt = self._evaluate_long_term(
                stock=stock,
                financial=financial,
                recent_financials=recent_financials,
                recent_prices=recent_prices,
                annual_total=all_annual_totals.get(stock.id),
                dividends=all_dividends.get(stock.id, []),
                cost_of_capital=cost_of_capital,
                growth_rate=growth_rate,
            )
            if lt is not None:
                long_term_candidates.append(lt)

            # ----- デイトレ候補 -----
            dt = self._evaluate_day_trade(
                stock=stock,
                recent_prices=recent_prices,
                high_low=all_52w.get(stock.id),
            )
            if dt is not None:
                day_trade_candidates.append(dt)

            # ----- レンジ候補 -----
            rb = self._evaluate_range_bound(
                stock=stock,
                recent_financials=recent_financials,
                recent_prices=recent_prices,
            )
            if rb is not None:
                range_candidates.append(rb)

        # スコア降順 → 上位 _TOP_N
        long_term_candidates.sort(key=lambda x: x[0], reverse=True)
        day_trade_candidates.sort(key=lambda x: x[0], reverse=True)
        range_candidates.sort(key=lambda x: x[0], reverse=True)

        return RecommendationsDTO(
            long_term=[r for _, r in long_term_candidates[:_TOP_N]],
            day_trade=[r for _, r in day_trade_candidates[:_TOP_N]],
            range_bound=[r for _, r in range_candidates[:_TOP_N]],
        )

    def _evaluate_long_term(
        self,
        stock: StockEntity,
        financial: FinancialEntity | None,
        recent_financials: list[FinancialEntity],
        recent_prices: list[PriceEntity],
        annual_total: Decimal | None,
        dividends: list[DividendEntity],
        cost_of_capital: Decimal,
        growth_rate: Decimal,
    ) -> tuple[Decimal, RecommendedStock] | None:
        """長期保有候補。

        - 適正株価より十分割安（10%以上）
        - EPS 3年 CAGR ≥ 3%（業績継続成長）
        - ROE ≥ 8%（資本効率高い）
        - 配当データがあれば加点（必須ではない）
        """
        if financial is None or stock.latest_price is None or financial.bps is None:
            return None

        # 業績成長
        gm = compute_growth_metrics(recent_financials)
        if gm.eps_cagr_3y is None or gm.eps_cagr_3y < _LONG_TERM_MIN_EPS_CAGR_3Y:
            return None
        if gm.eps_cagr_3y > _LONG_TERM_MAX_EPS_CAGR_3Y:
            # 赤字→黒字転換系の異常 CAGR を除外
            return None

        # 適正株価の算出（screening_usecase と同じく ROE>0 のみ条件）
        roe = financial.computed_roe
        if roe is None or roe <= 0:
            return None
        if roe < Decimal("0.08"):  # ROE 8% 未満は除外（資本効率の高さを担保）
            return None
        try:
            calc = FairValueCalculation(
                growth_rate=growth_rate,
                bps=financial.bps,
                current_price=stock.latest_price,
                roe=roe,
                cost_of_capital=cost_of_capital,
            )
            # fair_value > 0 のときのみ discount_rate が意味を持つ
            if calc.fair_value <= 0:
                return None
            discount_rate = calc.discount_rate
        except Exception:
            return None

        if discount_rate is None or discount_rate < _LONG_TERM_MIN_DISCOUNT_RATE:
            return None

        # 配当メトリクス（取得できない場合は加点なし）
        dm = compute_dividend_metrics(
            dividends=dividends,
            annual_total=annual_total,
            latest_price=stock.latest_price,
            eps=financial.eps,
        )

        # スコア
        score = (
            discount_rate * Decimal("100") * Decimal("1.0")  # 割安度（%換算）
            + gm.eps_cagr_3y * Decimal("100") * Decimal("0.5")  # 業績成長率（%換算）
            + roe * Decimal("100") * Decimal("0.2")  # ROE（%換算）
        )
        if dm.dividend_yield is not None:
            score += dm.dividend_yield * Decimal("0.5")

        metrics = {
            "discount_rate": f"{discount_rate * 100:.2f}",
            "eps_cagr_3y": f"{gm.eps_cagr_3y * 100:.2f}",
            "roe": f"{roe * 100:.2f}",
        }
        if dm.dividend_yield is not None:
            metrics["dividend_yield"] = f"{dm.dividend_yield:.2f}"
        if dm.consecutive_dividend_years is not None and dm.consecutive_dividend_years >= 1:
            metrics["consecutive_dividend_years"] = str(dm.consecutive_dividend_years)

        rec = RecommendedStock(
            code=stock.code,
            name=stock.name,
            latest_price=stock.latest_price,
            metrics=metrics,
            stock_id=stock.id or 0,
            score=score,
        )
        return (score, rec)

    def _evaluate_day_trade(
        self,
        stock: StockEntity,
        recent_prices: list,  # type: ignore[type-arg]
        high_low: tuple[Decimal, Decimal] | None,
    ) -> tuple[Decimal, RecommendedStock] | None:
        if stock.latest_price is None or stock.latest_price < _DAY_TRADE_MIN_PRICE:
            return None
        if not recent_prices:
            return None

        # 流動性レベル判定（既存 compute_technical_metrics の avg_turnover_20d を使う）
        tm = compute_technical_metrics(
            latest_price=stock.latest_price,
            high_low=high_low,
            recent_prices=recent_prices[:25],  # 既存仕様は最大25件
        )
        liquidity = _liquidity_level(tm.avg_turnover_20d)
        if liquidity not in _DAY_TRADE_LIQUIDITY_LEVELS:
            return None

        # ボラティリティ
        volatility = compute_volatility_20d(recent_prices)
        if volatility is None or volatility < _DAY_TRADE_MIN_VOLATILITY:
            return None

        # スコア: ボラ × 1.0 + (売買代金 / 10億円) × 0.5
        turnover_oku = (tm.avg_turnover_20d / Decimal("100000000")) if tm.avg_turnover_20d else Decimal(0)
        score = volatility + turnover_oku * Decimal("0.5")

        rec = RecommendedStock(
            code=stock.code,
            name=stock.name,
            latest_price=stock.latest_price,
            metrics={
                "volatility_20d": f"{volatility:.2f}",
                "avg_turnover_20d_oku": f"{turnover_oku:.1f}",
                "liquidity": liquidity or "-",
            },
            stock_id=stock.id or 0,
            score=score,
        )
        return (score, rec)

    def _evaluate_range_bound(
        self,
        stock: StockEntity,
        recent_financials: list,  # type: ignore[type-arg]
        recent_prices: list,  # type: ignore[type-arg]
    ) -> tuple[Decimal, RecommendedStock] | None:
        if stock.latest_price is None:
            return None

        rm = compute_range_metrics_1y(recent_prices)
        if rm is None:
            return None
        if rm.range_width < _RANGE_MIN_WIDTH:
            return None
        if abs(rm.drift_pct) > _RANGE_MAX_DRIFT_PCT:
            return None

        # 業績安定性（EPS 3年 CAGR が ±10% 以内）
        gm = compute_growth_metrics(recent_financials)
        if gm.eps_cagr_3y is None:
            return None
        eps_cagr_pct = gm.eps_cagr_3y * Decimal("100")
        if abs(eps_cagr_pct) > _RANGE_MAX_EPS_CAGR_PCT:
            return None

        # スコア: レンジ幅 / 100 - abs(drift) × 50
        score = rm.range_width / Decimal("100") - abs(rm.drift_pct) * Decimal("50")

        rec = RecommendedStock(
            code=stock.code,
            name=stock.name,
            latest_price=stock.latest_price,
            metrics={
                "range_high": f"{rm.high:.0f}",
                "range_low": f"{rm.low:.0f}",
                "range_width": f"{rm.range_width:.0f}",
                "drift_pct": f"{rm.drift_pct * 100:.2f}",
            },
            stock_id=stock.id or 0,
            score=score,
        )
        return (score, rec)


def _liquidity_level(avg_turnover_20d: Decimal | None) -> str | None:
    """売買代金20日平均から流動性レベルを判定（screening_usecase と同基準）。"""
    if avg_turnover_20d is None:
        return None
    if avg_turnover_20d >= Decimal("1000000000"):  # 10億円以上
        return "high"
    if avg_turnover_20d >= Decimal("100000000"):  # 1億円以上
        return "medium"
    if avg_turnover_20d >= Decimal("10000000"):  # 1000万円以上
        return "low"
    return "very_low"
