"""ETF一覧ユースケース。分配金利回り・52週リターン等を計算して返す。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
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
class EtfResult:
    """ETF分析結果。"""

    code: str
    name: str
    sector: str
    latest_price: Decimal | None
    latest_price_date: str | None
    annual_dividend: Decimal | None  # 直近12ヶ月配当合計
    dividend_yield: Decimal | None  # 分配金利回り = annual_dividend / latest_price
    return_52w: Decimal | None  # 52週リターン
    net_assets: int | None  # 純資産総額（百万円）
    latest_price_52w_ago: Decimal | None  # 52週前株価（参考）
    # バリュエーション評価
    evaluation_zone: str | None = None
    evaluation_score: int | None = None
    evaluation_signals: list[EvaluationSignal] = field(default_factory=list)
    price_position_52w: Decimal | None = None  # 52週価格位置 (0.0〜1.0)


def _compute_etf_valuation(
    dividend_yield: Decimal | None,
    price_position_52w: Decimal | None,
    return_52w: Decimal | None,
    net_assets: int | None,
) -> tuple[str, int, list[EvaluationSignal]]:
    """ETFバリュエーションを4ファクターでスコアリングする。"""
    signals: list[EvaluationSignal] = []
    score = 0

    # 分配金利回り
    if dividend_yield is not None:
        dy = float(dividend_yield)
        if dy >= 0.04:
            s = +2
            label = f"利回り {dy * 100:.1f}% — 高利回り"
        elif dy >= 0.025:
            s = +1
            label = f"利回り {dy * 100:.1f}% — 良好"
        elif dy >= 0.01:
            s = 0
            label = f"利回り {dy * 100:.1f}% — 標準"
        else:
            s = -1
            label = f"利回り {dy * 100:.1f}% — 低利回り"
        score += s
        signals.append(EvaluationSignal(category="分配金利回り", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="分配金利回り", label="データなし", impact=0))

    # 52週価格位置（最重要）
    if price_position_52w is not None:
        pp = float(price_position_52w)
        if pp < 0.20:
            s = +2
            label = f"52週位置 {pp * 100:.0f}% — 底値圏"
        elif pp < 0.40:
            s = +1
            label = f"52週位置 {pp * 100:.0f}% — やや安値"
        elif pp <= 0.60:
            s = 0
            label = f"52週位置 {pp * 100:.0f}% — 中間"
        elif pp <= 0.80:
            s = -1
            label = f"52週位置 {pp * 100:.0f}% — やや高値"
        else:
            s = -2
            label = f"52週位置 {pp * 100:.0f}% — 高値圏"
        score += s
        signals.append(EvaluationSignal(category="52週価格位置", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="52週価格位置", label="データなし", impact=0))

    # 52週リターン
    if return_52w is not None:
        r52 = float(return_52w)
        if r52 > 0.20:
            s = +1
            label = f"52週リターン {r52 * 100:.1f}% — 好調"
        elif r52 >= -0.10:
            s = 0
            label = f"52週リターン {r52 * 100:.1f}% — 中程度"
        else:
            s = -1
            label = f"52週リターン {r52 * 100:.1f}% — 不調"
        score += s
        signals.append(EvaluationSignal(category="52週リターン", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="52週リターン", label="データなし", impact=0))

    # 純資産残高
    if net_assets is not None:
        na_m = net_assets  # 百万円
        if na_m >= 10000:
            s = +1
            label = f"純資産 {na_m:,}百万円 — 大規模"
        elif na_m >= 100:
            s = 0
            label = f"純資産 {na_m:,}百万円 — 中規模"
        else:
            s = -1
            label = f"純資産 {na_m:,}百万円 — 小規模"
        score += s
        signals.append(EvaluationSignal(category="純資産残高", label=label, impact=s))
    else:
        signals.append(EvaluationSignal(category="純資産残高", label="データなし", impact=0))

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


class EtfScreeningUseCase:
    """ETF一覧を分配金利回り降順で返す。"""

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

    def execute(self, market_type: str = "JP") -> list[EtfResult]:
        """ETF一覧を返す。"""
        stocks = [
            s
            for s in self._stock_repo.find_by_market_type(market_type)
            if s.instrument_type == "etf" and s.id is not None
        ]

        results: list[EtfResult] = []
        target_52w = date.today() - timedelta(weeks=52)

        for stock in stocks:
            assert stock.id is not None

            annual_div = self._dividend_repo.find_annual_total(stock.id)
            dividend_yield: Decimal | None = None
            if annual_div is not None and stock.latest_price and stock.latest_price > 0:
                dividend_yield = (annual_div / stock.latest_price).quantize(Decimal("0.0001"))

            price_52w = self._price_repo.find_price_near_date(stock.id, target_52w)
            return_52w: Decimal | None = None
            if price_52w and price_52w > 0 and stock.latest_price:
                return_52w = ((stock.latest_price - price_52w) / price_52w).quantize(Decimal("0.0001"))

            financial = self._financial_repo.find_latest_by_stock_id(stock.id)

            # 52週価格位置
            price_position_52w: Decimal | None = None
            high_low = self._price_repo.find_52w_high_low(stock.id)
            if high_low and stock.latest_price:
                high, low = high_low
                if high > low:
                    price_position_52w = ((stock.latest_price - low) / (high - low)).quantize(Decimal("0.0001"))

            net_assets = financial.net_assets if financial else None

            # バリュエーション評価
            zone, eval_score, signals = _compute_etf_valuation(
                dividend_yield=dividend_yield,
                price_position_52w=price_position_52w,
                return_52w=return_52w,
                net_assets=net_assets,
            )

            results.append(
                EtfResult(
                    code=stock.code,
                    name=stock.name,
                    sector=stock.sector,
                    latest_price=stock.latest_price,
                    latest_price_date=str(stock.latest_price_date) if stock.latest_price_date else None,
                    annual_dividend=annual_div,
                    dividend_yield=dividend_yield,
                    return_52w=return_52w,
                    net_assets=net_assets,
                    latest_price_52w_ago=price_52w,
                    evaluation_zone=zone,
                    evaluation_score=eval_score,
                    evaluation_signals=signals,
                    price_position_52w=price_position_52w,
                )
            )

        # 利回りあり→降順、なし→末尾
        results.sort(key=lambda r: (r.dividend_yield is None, -(r.dividend_yield or Decimal(0))))
        logger.info("ETF一覧: %d 銘柄", len(results))
        return results
