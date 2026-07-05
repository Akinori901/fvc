from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime


@dataclass
class StockEntity:
    """銘柄エンティティ"""

    code: str
    name: str
    market: str = ""
    market_type: str = "JP"
    instrument_type: str = "stock"  # "stock" | "etf" | "reit" | "other"
    sector: str = ""
    is_active: bool = True
    is_active_override: bool | None = None  # None=自動判定, True=強制アクティブ, False=強制非アクティブ
    latest_price: Decimal | None = None
    latest_price_date: date | None = None
    id: int | None = None

    @property
    def effective_is_active(self) -> bool:
        """is_active_override が設定されていればそちらを優先する。"""
        if self.is_active_override is not None:
            return self.is_active_override
        return self.is_active


@dataclass
class FinancialEntity:
    """財務データエンティティ"""

    stock_id: int
    fiscal_year: int
    bps: Decimal
    eps: Decimal | None = None
    roe: Decimal | None = None
    net_assets: int | None = None
    total_shares: int | None = None
    revenue: int | None = None
    operating_income: int | None = None
    eps_forecast: Decimal | None = None
    operating_cash_flow: int | None = None  # 営業CF（百万円）
    free_cash_flow: int | None = None  # FCF（百万円）
    is_manual: bool = False  # True=手動入力データ（J-Quantsになければフォールバック）
    adj_factor: Decimal = Decimal("1")  # 決算期末時点の株式分割調整係数（BPS補正用）
    period_end_date: date | None = None  # J-Quants CurPerEn: 決算期末日
    id: int | None = None

    @property
    def computed_roe(self) -> Decimal | None:
        """EPS と BPS から ROE を計算。EPS がない場合は None を返す。

        NOTE: FinancialEntity.roe には J-Quants の EqAR（自己資本比率 = 自己資本/総資産）が
        格納されているが、これは ROE（Return on Equity = EPS/BPS）とは別指標であるため、
        代替として使用しない。ROE は必ず EPS/BPS から計算する。
        """
        if self.eps is not None and self.bps and self.bps != 0:
            return self.eps / self.bps
        return None

    @property
    def company_forecast_growth_rate(self) -> Decimal | None:
        """会社予想成長率 = (ForecastEPS - EPS) / |EPS|"""
        if self.eps_forecast is None or self.eps is None or self.eps == 0:
            return None
        return (self.eps_forecast - self.eps) / abs(self.eps)


@dataclass
class PriceEntity:
    """株価エンティティ"""

    stock_id: int
    date: str
    close_price: Decimal
    adj_factor: Decimal = Decimal("1")  # 株式分割等の権利調整係数
    pbr: Decimal | None = None
    volume: int | None = None
    is_limit_up: bool = False  # J-Quants UL: 日通ストップ高
    is_limit_down: bool = False  # J-Quants LL: 日通ストップ安
    id: int | None = None


@dataclass
class StockWithFinancials:
    """銘柄 + 最新財務データ"""

    stock: StockEntity
    latest_financial: FinancialEntity | None = None
    latest_price: PriceEntity | None = None
    financials: list[FinancialEntity] = field(default_factory=list)


@dataclass
class ApiConfigEntity:
    """API設定エンティティ"""

    provider: str
    is_enabled: bool = False
    api_key: str = ""
    plan: str = ""
    config_json: dict[str, object] = field(default_factory=dict)
    id: int | None = None


@dataclass
class DividendEntity:
    """配当・分配金エンティティ"""

    stock_id: int
    ex_dividend_date: date
    dividends_per_share: Decimal
    record_date: date | None = None
    payable_date: date | None = None
    source: str = "yfinance"
    id: int | None = None


@dataclass
class MarginBalanceEntity:
    """信用取引残高エンティティ"""

    stock_id: int
    date: date
    long_balance: int | None = None  # 信用買残（株数）
    long_balance_change: int | None = None  # 信用買残変化
    short_balance: int | None = None  # 信用売残（株数）
    short_balance_change: int | None = None  # 信用売残変化
    sl_ratio: Decimal | None = None  # 信売比率
    id: int | None = None


@dataclass
class DailyMoversEntity:
    """日次の急騰急落集計エンティティ。

    バッチ (compute_movers) で日次に t_daily_movers へ書き込まれる。
    """

    stock_id: int
    date: date
    close_price: Decimal
    prev_close: Decimal | None  # 前営業日の終値（DB 上の直前レコード基準）
    change_pct: Decimal | None  # 前日比 (%)、例: 21.2800
    volume: int | None
    volume_ratio_20d: Decimal | None  # 出来高 20 日平均比
    is_limit_up: bool = False
    is_limit_down: bool = False
    id: int | None = None


@dataclass
class OwnerShareholderEntity:
    """代表者-大株主紐付けエンティティ"""

    stock_id: int
    representative_name: str
    shareholder_name: str
    shareholder_rank: int
    ownership_ratio: Decimal
    match_type: str  # "exact" / "family" / "company"
    fiscal_year: int
    doc_id: str
    id: int | None = None


@dataclass
class ShareholderRawEntity:
    """大株主生データエンティティ"""

    stock_id: int
    shareholder_name: str
    shareholder_rank: int
    ownership_ratio: Decimal
    fiscal_year: int
    doc_id: str
    shares_held: int | None = None
    id: int | None = None


@dataclass
class SyncLogEntity:
    """同期ログエンティティ"""

    sync_type: str
    provider: str
    market: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    error_details: list[dict[str, str]] = field(default_factory=list)
    id: int | None = None
