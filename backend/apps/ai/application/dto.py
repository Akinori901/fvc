"""AI機能DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


@dataclass
class AiConfigDTO:
    provider: str
    model: str
    is_enabled: bool
    has_api_key: bool
    updated_at: datetime | None = None


@dataclass
class StockContextDTO:
    """プロンプトに渡す銘柄コンテキスト。

    基本財務に加え、画面の「スクリーニング指標」相当（成長性・テクニカル・
    需給・配当・FCF・オーナー経営）を ScreeningResult から取り込む。
    追加項目はすべて任意（データ欠損時は None → プロンプトで「不明」表記）。
    """

    code: str
    name: str
    sector: str
    latest_price: Decimal | None
    bps: Decimal | None
    eps: Decimal | None
    roe: Decimal | None
    revenue: int | None
    operating_income: int | None
    pbr: Decimal | None
    fair_value: Decimal | None
    discount_rate: Decimal | None

    # --- 成長性 ---
    implied_growth_rate: Decimal | None = None  # 市場折込成長率
    company_forecast_growth_rate: Decimal | None = None  # 会社予想成長率
    growth_rate_label: str | None = None  # 成長率評価ラベル
    eps_growth_yoy: Decimal | None = None  # EPS成長率（前年比, %）
    eps_cagr_3y: Decimal | None = None  # EPS CAGR（3年, %）
    roe_trend: str | None = None  # improving / declining / stable
    revenue_growth_yoy: Decimal | None = None  # 売上高成長率（前年比, %）

    # --- テクニカル・需給 ---
    sl_ratio: Decimal | None = None  # 信用倍率（信売比率）
    long_balance_trend: str | None = None  # 信用買残トレンド increasing/decreasing/flat
    momentum_signal: str | None = None  # strong_buy / buy / neutral / caution / sell
    price_position_52w: Decimal | None = None  # 52週レンジ内の位置（%）
    distance_from_52w_high: Decimal | None = None  # 52週高値からの距離（%）
    liquidity_level: str | None = None  # high / medium / low / very_low

    # --- 配当 ---
    dividend_yield: Decimal | None = None  # 配当利回り（%）
    payout_ratio: Decimal | None = None  # 配当性向（%）
    consecutive_dividend_years: int | None = None  # 連続配当年数
    progressive_dividend_years: int | None = None  # 累進配当年数

    # --- FCF ---
    fcf_yield: Decimal | None = None  # FCF利回り（%）
    fcf_margin: Decimal | None = None  # FCFマージン（%）

    # --- オーナー経営 ---
    is_owner_managed: bool = False
    owner_ratio: Decimal | None = None  # 代表者関連の持株比率合計（%）

    # --- テクニカル詳細（build_indicators の最新値。日足終値ベース） ---
    ma_25_deviation_pct: Decimal | None = None  # 25日移動平均乖離率（%）
    ma_75_deviation_pct: Decimal | None = None  # 75日移動平均乖離率（%）
    ma_200_deviation_pct: Decimal | None = None  # 200日移動平均乖離率（%）
    rsi_14: Decimal | None = None  # RSI(14)
    rsi_signal: str | None = None  # overbought / oversold / neutral
    macd_hist: Decimal | None = None  # MACD ヒストグラム
    macd_cross: str | None = None  # golden / dead / none
    bb_position: Decimal | None = None  # ボリンジャーバンド %B
    bb_signal: str | None = None  # above_upper / below_lower / inside
    atr_pct: Decimal | None = None  # ATR(14) の株価比（%, close-to-close近似）
    volatility_20d: Decimal | None = None  # ヒストリカル・ボラティリティ（20日, %）

    # --- 財務健全性 ---
    equity_ratio: Decimal | None = None  # 自己資本比率（%, J-Quants EqAR）
    operating_margin: Decimal | None = None  # 営業利益率（%）
    operating_cash_flow: int | None = None  # 営業CF（百万円）
    free_cash_flow: int | None = None  # FCF（百万円）
    market_cap: int | None = None  # 時価総額（百万円）
    per: Decimal | None = None  # PER（倍）

    # --- 市場環境（マクロ。銘柄個別ではなく環境情報） ---
    usdjpy: Decimal | None = None  # USD/JPY 直近
    jp_10y: Decimal | None = None  # 日本10年債利回り（%）
    us_10y: Decimal | None = None  # 米国10年債利回り（%）
    market_type: str = "JP"  # JP / US（コスト・オブ・キャピタルや金利感応の前提）


@dataclass
class AnalysisRequestDTO:
    user_id: int
    stock_code: str
    question_type: str
    custom_question: str = ""
    expert_role: str = "general"


@dataclass
class AnalysisResultDTO:
    analysis: str
    model: str
    generated_at: datetime
    prompt_tokens: int
    completion_tokens: int
