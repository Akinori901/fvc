"""FX分析サービス（核心ロジック）。

金利差回帰モデル + テクニカル指標 + PPP 乖離率 を計算する。
OLS 回帰は pure Python（numpy/scipy 不使用）で Lambda パッケージサイズを抑制。
"""

from __future__ import annotations

import logging
from decimal import Decimal
from math import sqrt
from typing import TYPE_CHECKING

from ...domain.entities import (
    FxAnalysisResult,
    FxRateEntity,
    RegressionResult,
    TechnicalIndicators,
)

if TYPE_CHECKING:
    from datetime import date

    from ...domain.entities import InterestRateEntity
    from ...domain.repositories import FxRateRepository, InterestRateRepository, MacroIndicatorRepository

logger = logging.getLogger(__name__)

_D = Decimal
_Q4 = Decimal("0.0001")
_Q2 = Decimal("0.01")


class FxAnalysisService:
    """FX 分析サービス"""

    def __init__(
        self,
        fx_rate_repo: FxRateRepository,
        interest_rate_repo: InterestRateRepository,
        macro_indicator_repo: MacroIndicatorRepository,
    ) -> None:
        self._fx_rate_repo = fx_rate_repo
        self._interest_rate_repo = interest_rate_repo
        self._macro_indicator_repo = macro_indicator_repo

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def analyze(self) -> FxAnalysisResult:
        """FX 分析を実行し結果を返す。"""
        # データ取得
        fx_rates = self._fx_rate_repo.find_all(pair="USDJPY")
        us_rates = self._interest_rate_repo.find_all("US", "10Y")
        jp_rates = self._interest_rate_repo.find_all("JP", "10Y")

        if not fx_rates:
            from ...domain.exceptions import FxDataNotFoundError

            raise FxDataNotFoundError("為替レートデータがありません。sync_fx_data を実行してください。")

        latest_fx = fx_rates[-1]

        # 最新金利
        latest_us = us_rates[-1] if us_rates else None
        latest_jp = jp_rates[-1] if jp_rates else None
        us_10y = latest_us.rate if latest_us else None
        jp_10y = latest_jp.rate if latest_jp else None
        interest_rate_diff = (us_10y - jp_10y) if (us_10y is not None and jp_10y is not None) else None

        # 回帰分析
        regression = None
        chart_data: list[dict[str, object]] = []
        if us_rates and jp_rates and len(fx_rates) >= 30:
            regression, chart_data = self._compute_regression(fx_rates, us_rates, jp_rates)

        # テクニカル指標
        technicals = self._compute_technicals(fx_rates)

        # PPP
        ppp_indicator = self._macro_indicator_repo.find_latest("PPP_USDJPY")
        ppp_rate = ppp_indicator.value if ppp_indicator else None
        ppp_deviation = None
        if ppp_rate and ppp_rate != 0:
            ppp_deviation = ((latest_fx.close_rate - ppp_rate) / ppp_rate * 100).quantize(_Q2)

        # ゾーン境界
        buy_zone_lower = sell_zone_upper = strong_buy_lower = strong_sell_upper = None
        if regression:
            buy_zone_lower = regression.fair_value - regression.residual_std
            sell_zone_upper = regression.fair_value + regression.residual_std
            strong_buy_lower = regression.fair_value - regression.residual_std * 2
            strong_sell_upper = regression.fair_value + regression.residual_std * 2

        return FxAnalysisResult(
            current_rate=latest_fx.close_rate,
            current_rate_date=latest_fx.date,
            us_10y=us_10y,
            jp_10y=jp_10y,
            interest_rate_diff=interest_rate_diff,
            regression=regression,
            technicals=technicals,
            ppp_rate=ppp_rate,
            ppp_deviation=ppp_deviation,
            buy_zone_lower=buy_zone_lower,
            sell_zone_upper=sell_zone_upper,
            strong_buy_lower=strong_buy_lower,
            strong_sell_upper=strong_sell_upper,
            chart_data=chart_data,
        )

    # ------------------------------------------------------------------
    # OLS 回帰
    # ------------------------------------------------------------------

    def _compute_regression(
        self,
        fx_rates: list[FxRateEntity],
        us_rates: list[InterestRateEntity],
        jp_rates: list[InterestRateEntity],
    ) -> tuple[RegressionResult, list[dict[str, object]]]:
        """純 Python OLS 回帰: USDJPY = β₀ + β₁ × (US10Y - JP10Y)"""
        # 金利を date → rate 辞書に変換（JP は forward-fill）
        us_map = {r.date: float(r.rate) for r in us_rates}
        jp_daily = self._forward_fill_monthly(jp_rates, fx_rates)

        # 共通日付のペアを作成
        pairs: list[tuple[float, float]] = []
        chart_data: list[dict[str, object]] = []
        for fx in fx_rates:
            us_val = us_map.get(fx.date)
            jp_val = jp_daily.get(fx.date)
            if us_val is not None and jp_val is not None:
                diff = us_val - jp_val
                pairs.append((diff, float(fx.close_rate)))

        if len(pairs) < 30:
            raise ValueError("回帰に必要なデータ点が不足しています")

        # OLS 計算
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        n = len(xs)
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n

        ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
        ss_xx = sum((x - x_mean) ** 2 for x in xs)

        if ss_xx == 0:
            raise ValueError("金利差のバリエーションがゼロです")

        beta_1 = ss_xy / ss_xx
        beta_0 = y_mean - beta_1 * x_mean

        # 残差・R²
        residuals = [y - (beta_0 + beta_1 * x) for x, y in zip(xs, ys, strict=True)]
        ss_res = sum(r**2 for r in residuals)
        ss_tot = sum((y - y_mean) ** 2 for y in ys)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else _D("0")
        residual_std = sqrt(ss_res / n) if n > 0 else 0

        # 現在の適正値
        latest_diff = xs[-1]
        fair_value = beta_0 + beta_1 * latest_diff
        current_rate = ys[-1]
        deviation = current_rate - fair_value

        # ゾーン判定
        if deviation <= -2 * residual_std:
            zone = "strong_buy"
        elif deviation <= -residual_std:
            zone = "buy"
        elif deviation >= 2 * residual_std:
            zone = "strong_sell"
        elif deviation >= residual_std:
            zone = "sell"
        else:
            zone = "neutral"

        # チャートデータ作成
        for fx in fx_rates:
            us_val = us_map.get(fx.date)
            jp_val = jp_daily.get(fx.date)
            entry: dict[str, object] = {
                "date": fx.date.isoformat(),
                "rate": str(fx.close_rate),
            }
            if us_val is not None and jp_val is not None:
                diff = us_val - jp_val
                fv = beta_0 + beta_1 * diff
                entry["fair_value"] = str(_D(str(fv)).quantize(_Q4))
                entry["upper_1s"] = str(_D(str(fv + residual_std)).quantize(_Q4))
                entry["lower_1s"] = str(_D(str(fv - residual_std)).quantize(_Q4))
                entry["upper_2s"] = str(_D(str(fv + 2 * residual_std)).quantize(_Q4))
                entry["lower_2s"] = str(_D(str(fv - 2 * residual_std)).quantize(_Q4))
            chart_data.append(entry)

        regression = RegressionResult(
            beta_0=_D(str(beta_0)).quantize(_Q4),
            beta_1=_D(str(beta_1)).quantize(_Q4),
            fair_value=_D(str(fair_value)).quantize(_Q4),
            residual_std=_D(str(residual_std)).quantize(_Q4),
            r_squared=_D(str(r_squared)).quantize(_Q4),
            current_deviation=_D(str(deviation)).quantize(_Q4),
            zone=zone,
        )

        return regression, chart_data

    @staticmethod
    def _forward_fill_monthly(
        monthly_rates: list[InterestRateEntity],
        fx_rates: list[FxRateEntity],
    ) -> dict[date, float]:
        """月次データを日次に前方補完 (forward-fill)。"""
        if not monthly_rates:
            return {}

        # 月次データをソート
        sorted_rates = sorted(monthly_rates, key=lambda r: r.date)
        result: dict[date, float] = {}

        # 各 FX 日付に対して、最も近い過去の月次データを適用
        rate_idx = 0
        fx_dates = sorted(fx.date for fx in fx_rates)

        for fx_date in fx_dates:
            while rate_idx < len(sorted_rates) - 1 and sorted_rates[rate_idx + 1].date <= fx_date:
                rate_idx += 1
            if sorted_rates[rate_idx].date <= fx_date:
                result[fx_date] = float(sorted_rates[rate_idx].rate)

        return result

    # ------------------------------------------------------------------
    # テクニカル指標
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_technicals(fx_rates: list[FxRateEntity]) -> TechnicalIndicators:
        """RSI(14), ボリンジャーバンド(20,2), 200日移動平均を計算。"""
        if not fx_rates:
            return TechnicalIndicators()

        closes = [float(r.close_rate) for r in fx_rates]
        current = closes[-1]

        # RSI (14)
        rsi_14 = None
        if len(closes) >= 15:
            rsi_14 = _D(str(FxAnalysisService._calc_rsi(closes, 14))).quantize(_Q2)

        # ボリンジャーバンド (20, 2)
        bb_upper = bb_middle = bb_lower = None
        if len(closes) >= 20:
            window = closes[-20:]
            mean = sum(window) / len(window)
            std = sqrt(sum((x - mean) ** 2 for x in window) / len(window))
            bb_middle = _D(str(mean)).quantize(_Q4)
            bb_upper = _D(str(mean + 2 * std)).quantize(_Q4)
            bb_lower = _D(str(mean - 2 * std)).quantize(_Q4)

        # 200日移動平均
        ma_200 = ma_200_deviation = None
        if len(closes) >= 200:
            ma = sum(closes[-200:]) / 200
            ma_200 = _D(str(ma)).quantize(_Q4)
            if ma != 0:
                ma_200_deviation = _D(str((current - ma) / ma * 100)).quantize(_Q2)

        return TechnicalIndicators(
            rsi_14=rsi_14,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            ma_200=ma_200,
            ma_200_deviation=ma_200_deviation,
        )

    @staticmethod
    def _calc_rsi(closes: list[float], period: int = 14) -> float:
        """RSI を計算。"""
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
