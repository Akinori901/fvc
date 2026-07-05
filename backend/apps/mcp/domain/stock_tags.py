"""銘柄リスク・機会タグの判定純関数。

ScreeningResult と任意の追加指標（RSI 等）からタグを算出する。
ドメイン純関数として副作用なしで実装し、UseCase 側はこの関数を呼ぶだけにする。

タグ語彙はリスク 4 種 / 機会 4 種の計 8 種を初版とする（PR3 で拡張予定）。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.stocks.application.usecases.screening_usecase import ScreeningResult


# ============================================================
# しきい値定数（実運用後に調整可能）
# ============================================================

# 信用過熱判定
_MARGIN_OVERHANG_LONG_THRESHOLD = 300_000  # 株
_MARGIN_OVERHANG_CREDIT_RATIO_THRESHOLD = Decimal("5")  # 信用倍率

# 流動性判定
_LOW_LIQUIDITY_TURNOVER_THRESHOLD = Decimal("100000000")  # 売買代金 1 億円

# 過大評価判定
_OVERVALUED_PBR_MULTIPLE = Decimal("2")  # current_pbr > fair_pbr × N

# 連続増配
_PROGRESSIVE_DIVIDEND_THRESHOLD_YEARS = 5

# 52w 下端接近
_NEAR_52W_LOW_POSITION_THRESHOLD = Decimal("0.10")

# RSI 売られすぎ判定
_OVERSOLD_RSI_THRESHOLD = Decimal("30")


# ============================================================
# 出力型
# ============================================================


@dataclass(frozen=True)
class StockTag:
    """個別タグ。severity は high / medium / low の 3 段階。"""

    tag: str
    severity: str
    detail: str


# ============================================================
# リスクタグ
# ============================================================


def compute_risk_tags(result: ScreeningResult) -> list[StockTag]:
    """ScreeningResult からリスクタグのリストを返す。"""
    tags: list[StockTag] = []

    margin_tag = _check_high_margin_overhang(result)
    if margin_tag is not None:
        tags.append(margin_tag)

    liquidity_tag = _check_low_liquidity(result)
    if liquidity_tag is not None:
        tags.append(liquidity_tag)

    overvalued_tag = _check_overvalued_relative(result)
    if overvalued_tag is not None:
        tags.append(overvalued_tag)

    no_fv_tag = _check_no_fair_value(result)
    if no_fv_tag is not None:
        tags.append(no_fv_tag)

    return tags


def _check_high_margin_overhang(result: ScreeningResult) -> StockTag | None:
    """信用買い残オーバーハング: 売残 0 で買残大 OR 信用倍率 > 5。"""
    long_balance = result.long_balance
    short_balance = result.short_balance

    if long_balance is None or long_balance <= 0:
        return None

    if short_balance == 0 and long_balance > _MARGIN_OVERHANG_LONG_THRESHOLD:
        return StockTag(
            tag="risk_high_margin_overhang",
            severity="high",
            detail=f"信用買い残 {long_balance:,} 株 / 売残 0（信用倍率算出不可）",
        )

    if short_balance is not None and short_balance > 0:
        ratio = Decimal(long_balance) / Decimal(short_balance)
        if ratio > _MARGIN_OVERHANG_CREDIT_RATIO_THRESHOLD:
            return StockTag(
                tag="risk_high_margin_overhang",
                severity="high",
                detail=f"信用倍率 {ratio:.1f}（買 {long_balance:,} / 売 {short_balance:,}）",
            )

    return None


def _check_low_liquidity(result: ScreeningResult) -> StockTag | None:
    """流動性低: 売買代金 20 日平均 < 1 億円。"""
    turnover = result.avg_turnover_20d
    if turnover is None:
        return None
    if turnover >= _LOW_LIQUIDITY_TURNOVER_THRESHOLD:
        return None
    return StockTag(
        tag="risk_low_liquidity",
        severity="medium",
        detail=f"売買代金 20 日平均 {turnover:,.0f} 円（< 1 億円）",
    )


def _check_overvalued_relative(result: ScreeningResult) -> StockTag | None:
    """過大評価: current_pbr > fair_pbr × 2。"""
    current_pbr = result.current_pbr
    fair_pbr = result.fair_pbr
    if current_pbr is None or fair_pbr is None or fair_pbr <= 0:
        return None
    if current_pbr <= fair_pbr * _OVERVALUED_PBR_MULTIPLE:
        return None
    multiple = current_pbr / fair_pbr
    return StockTag(
        tag="risk_overvalued_relative",
        severity="medium",
        detail=f"現 PBR {current_pbr} は適正 PBR {fair_pbr} の {multiple:.2f} 倍",
    )


def _check_no_fair_value(result: ScreeningResult) -> StockTag | None:
    """フェアバリュー算出不可: 投資判断時の注意喚起。"""
    if result.fair_value is not None:
        return None
    reason = result.not_calculable_reason or "不明"
    return StockTag(
        tag="risk_no_fair_value",
        severity="low",
        detail=f"適正株価が算出不可（理由: {reason}）",
    )


# ============================================================
# 機会タグ
# ============================================================


def compute_opportunity_tags(
    result: ScreeningResult,
    rsi_14: Decimal | None = None,
) -> list[StockTag]:
    """ScreeningResult と任意の RSI から機会タグのリストを返す。"""
    tags: list[StockTag] = []

    dividend_tag = _check_consecutive_dividend_increase(result)
    if dividend_tag is not None:
        tags.append(dividend_tag)

    low_tag = _check_near_52w_low(result)
    if low_tag is not None:
        tags.append(low_tag)

    value_tag = _check_value_zone(result)
    if value_tag is not None:
        tags.append(value_tag)

    rsi_tag = _check_oversold_rsi(rsi_14)
    if rsi_tag is not None:
        tags.append(rsi_tag)

    return tags


def _check_consecutive_dividend_increase(result: ScreeningResult) -> StockTag | None:
    """累進配当年数 >= 5。"""
    years = result.progressive_dividend_years
    if years is None or years < _PROGRESSIVE_DIVIDEND_THRESHOLD_YEARS:
        return None
    return StockTag(
        tag="opportunity_consecutive_dividend_increase",
        severity="high",
        detail=f"累進配当 {years} 年（5 年以上）",
    )


def _check_near_52w_low(result: ScreeningResult) -> StockTag | None:
    """52w レンジの下端 10% 以内。"""
    position = result.price_position_52w
    if position is None or position > _NEAR_52W_LOW_POSITION_THRESHOLD:
        return None
    return StockTag(
        tag="opportunity_near_52w_low",
        severity="medium",
        detail=f"52w レンジ位置 {position:.2%}（下端から 10% 以内）",
    )


def _check_value_zone(result: ScreeningResult) -> StockTag | None:
    """evaluation_zone が cheap 系。"""
    zone = result.evaluation_zone
    if zone not in ("very_cheap", "cheap"):
        return None
    severity = "high" if zone == "very_cheap" else "medium"
    return StockTag(
        tag="opportunity_value_zone",
        severity=severity,
        detail=f"評価ゾーン: {zone}",
    )


def _check_oversold_rsi(rsi_14: Decimal | None) -> StockTag | None:
    """RSI 14 < 30。"""
    if rsi_14 is None or rsi_14 >= _OVERSOLD_RSI_THRESHOLD:
        return None
    return StockTag(
        tag="opportunity_oversold_rsi",
        severity="medium",
        detail=f"RSI 14 = {rsi_14}（< 30、売られすぎ水準）",
    )
