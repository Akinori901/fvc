"""FX分析ドメインエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal


@dataclass
class FxRateEntity:
    """為替レートエンティティ（日次）"""

    date: date
    pair: str  # "USDJPY"
    close_rate: Decimal
    id: int | None = None


@dataclass
class InterestRateEntity:
    """金利エンティティ"""

    date: date
    country: str  # "US" | "JP"
    rate_type: str  # "10Y"
    rate: Decimal
    id: int | None = None


@dataclass
class MacroIndicatorEntity:
    """マクロ指標エンティティ（年次PPP等）"""

    indicator_type: str  # "PPP_USDJPY"
    value: Decimal
    year: int
    source: str  # "OECD"
    id: int | None = None


@dataclass
class TechnicalIndicators:
    """テクニカル指標（計算結果）"""

    rsi_14: Decimal | None = None
    bb_upper: Decimal | None = None
    bb_middle: Decimal | None = None
    bb_lower: Decimal | None = None
    ma_200: Decimal | None = None
    ma_200_deviation: Decimal | None = None  # %


@dataclass
class RegressionResult:
    """回帰分析結果"""

    beta_0: Decimal  # 切片
    beta_1: Decimal  # 金利差の係数
    fair_value: Decimal  # 現在の金利差での予測値
    residual_std: Decimal  # 残差の標準偏差
    r_squared: Decimal
    current_deviation: Decimal  # 現在レート - 適正値
    zone: str  # "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell"


@dataclass
class FxAnalysisResult:
    """FX分析結果"""

    current_rate: Decimal
    current_rate_date: date
    us_10y: Decimal | None
    jp_10y: Decimal | None
    interest_rate_diff: Decimal | None
    regression: RegressionResult | None
    technicals: TechnicalIndicators
    ppp_rate: Decimal | None
    ppp_deviation: Decimal | None  # (current - ppp) / ppp
    buy_zone_lower: Decimal | None = None  # fair_value - 1σ
    sell_zone_upper: Decimal | None = None  # fair_value + 1σ
    strong_buy_lower: Decimal | None = None  # fair_value - 2σ
    strong_sell_upper: Decimal | None = None  # fair_value + 2σ
    chart_data: list[dict[str, object]] = field(default_factory=list)
