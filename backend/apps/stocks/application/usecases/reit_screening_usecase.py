"""REIT一覧ユースケース。P/NAV・分配金利回り等を計算して返す。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import (
        DividendRepository,
        FinancialRepository,
        PriceRepository,
        StockRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class EvaluationSignal:
    """評価シグナル。"""

    category: str
    label: str
    impact: int


@dataclass
class ReitResult:
    """REIT分析結果。"""

    code: str
    name: str
    sector: str
    latest_price: Decimal | None
    latest_price_date: str | None
    bps: Decimal | None  # 1口あたりNAV
    p_nav: Decimal | None  # P/NAV = 株価 / BPS
    annual_dividend: Decimal | None  # 直近12ヶ月分配金合計
    dividend_yield: Decimal | None  # 分配金利回り = annual_dividend / latest_price
    eps: Decimal | None  # 1口あたり利益
    # バリュエーション評価
    evaluation_zone: str | None = None
    evaluation_score: int | None = None
    evaluation_signals: list[EvaluationSignal] = field(default_factory=list)
    price_position_52w: Decimal | None = None  # 52週価格位置 (0.0〜1.0)
    payout_coverage: Decimal | None = None  # 分配カバレッジ = EPS / 年間分配金


def _compute_reit_valuation(
    p_nav: Decimal | None,
    dividend_yield: Decimal | None,
    payout_coverage: Decimal | None,
    price_position_52w: Decimal | None,
) -> tuple[str, int, list[EvaluationSignal]]:
    """REITバリュエーションを4ファクターでスコアリングする。"""
    signals: list[EvaluationSignal] = []
    score = 0

    # P/NAV（最重要）
    if p_nav is not None:
        pn = float(p_nav)
        if pn < 0.8:
            s = +3
            label = f"P/NAV {pn:.2f} — 大幅割安（NAVの80%未満）"
        elif pn < 0.95:
            s = +1
            label = f"P/NAV {pn:.2f} — 割安"
        elif pn <= 1.10:
            s = 0
            label = f"P/NAV {pn:.2f} — 適正"
        elif pn <= 1.30:
            s = -2
            label = f"P/NAV {pn:.2f} — 割高"
        else:
            s = -3
            label = f"P/NAV {pn:.2f} — 大幅割高"
        score += s
        signals.append(EvaluationSignal(category="P/NAV", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="P/NAV", label="データなし", impact=0))

    # 分配金利回り
    if dividend_yield is not None:
        dy = float(dividend_yield)
        if dy >= 0.055:
            s = +2
            label = f"利回り {dy * 100:.1f}% — 高利回り"
        elif dy >= 0.045:
            s = +1
            label = f"利回り {dy * 100:.1f}% — 良好"
        elif dy >= 0.035:
            s = 0
            label = f"利回り {dy * 100:.1f}% — 標準"
        elif dy >= 0.025:
            s = -1
            label = f"利回り {dy * 100:.1f}% — 低め"
        else:
            s = -2
            label = f"利回り {dy * 100:.1f}% — 低利回り"
        score += s
        signals.append(EvaluationSignal(category="分配金利回り", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="分配金利回り", label="データなし", impact=0))

    # 分配カバレッジ (EPS / 年間分配金)
    if payout_coverage is not None:
        pc = float(payout_coverage)
        if pc >= 1.2:
            s = +1
            label = f"カバレッジ {pc:.2f}x — 余裕あり"
        elif pc >= 1.0:
            s = 0
            label = f"カバレッジ {pc:.2f}x — 適正"
        elif pc >= 0.8:
            s = -1
            label = f"カバレッジ {pc:.2f}x — やや不足"
        else:
            s = -2
            label = f"カバレッジ {pc:.2f}x — 不足"
        score += s
        signals.append(EvaluationSignal(category="分配カバレッジ", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="分配カバレッジ", label="データなし", impact=0))

    # 52週価格位置
    if price_position_52w is not None:
        pp = float(price_position_52w)
        if pp < 0.20:
            s = +1
            label = f"52週位置 {pp * 100:.0f}% — 底値圏"
        elif pp <= 0.80:
            s = 0
            label = f"52週位置 {pp * 100:.0f}% — 中間"
        else:
            s = -1
            label = f"52週位置 {pp * 100:.0f}% — 高値圏"
        score += s
        signals.append(EvaluationSignal(category="52週価格位置", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="52週価格位置", label="データなし", impact=0))

    # ゾーン判定
    if score >= 4:
        zone = "超割安"
    elif score >= 2:
        zone = "買い推奨"
    elif score >= -1:
        zone = "レンジ中"
    elif score >= -3:
        zone = "下落警戒"
    else:
        zone = "購入危険"

    return zone, score, signals


class ReitScreeningUseCase:
    """REIT一覧を分配金利回り降順で返す。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        financial_repo: FinancialRepository,
        dividend_repo: DividendRepository,
        price_repo: PriceRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._financial_repo = financial_repo
        self._dividend_repo = dividend_repo
        self._price_repo = price_repo

    def execute(self, market_type: str = "JP") -> list[ReitResult]:
        """REIT一覧を返す。"""
        stocks = [
            s
            for s in self._stock_repo.find_by_market_type(market_type)
            if s.instrument_type == "reit" and s.id is not None
        ]

        results: list[ReitResult] = []

        for stock in stocks:
            assert stock.id is not None

            financial = self._financial_repo.find_latest_by_stock_id(stock.id)
            bps = financial.bps if financial else None
            eps = financial.eps if financial else None

            p_nav: Decimal | None = None
            if stock.latest_price and bps and bps > 0:
                p_nav = (stock.latest_price / bps).quantize(Decimal("0.0001"))

            annual_div = self._dividend_repo.find_annual_total(stock.id)
            dividend_yield: Decimal | None = None
            if annual_div is not None and stock.latest_price and stock.latest_price > 0:
                dividend_yield = (annual_div / stock.latest_price).quantize(Decimal("0.0001"))

            # 分配カバレッジ
            payout_coverage: Decimal | None = None
            if eps is not None and annual_div is not None and annual_div > 0:
                payout_coverage = (eps / annual_div).quantize(Decimal("0.01"))

            # 52週価格位置
            price_position_52w: Decimal | None = None
            high_low = self._price_repo.find_52w_high_low(stock.id)
            if high_low and stock.latest_price:
                high, low = high_low
                if high > low:
                    price_position_52w = ((stock.latest_price - low) / (high - low)).quantize(Decimal("0.0001"))

            # バリュエーション評価
            zone, eval_score, signals = _compute_reit_valuation(
                p_nav=p_nav,
                dividend_yield=dividend_yield,
                payout_coverage=payout_coverage,
                price_position_52w=price_position_52w,
            )

            results.append(
                ReitResult(
                    code=stock.code,
                    name=stock.name,
                    sector=stock.sector,
                    latest_price=stock.latest_price,
                    latest_price_date=str(stock.latest_price_date) if stock.latest_price_date else None,
                    bps=bps,
                    p_nav=p_nav,
                    annual_dividend=annual_div,
                    dividend_yield=dividend_yield,
                    eps=eps,
                    evaluation_zone=zone,
                    evaluation_score=eval_score,
                    evaluation_signals=signals,
                    price_position_52w=price_position_52w,
                    payout_coverage=payout_coverage,
                )
            )

        # 利回りあり→降順、なし→末尾
        results.sort(key=lambda r: (r.dividend_yield is None, -(r.dividend_yield or Decimal(0))))
        logger.info("REIT一覧: %d 銘柄", len(results))
        return results
