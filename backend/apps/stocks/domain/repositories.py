from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date

    from .entities import (
        ApiConfigEntity,
        DailyMoversEntity,
        DividendEntity,
        FinancialEntity,
        MarginBalanceEntity,
        OwnerShareholderEntity,
        PriceEntity,
        ShareholderRawEntity,
        StockEntity,
        SyncLogEntity,
    )
    from .screening_preset import ScreeningPresetEntity

# ============================================================
# データ転送オブジェクト（外部APIからの取得データ）
# ============================================================


@dataclass
class MarketStockData:
    """外部APIから取得した銘柄データ"""

    code: str
    name: str
    market: str
    market_type: str
    sector: str
    instrument_type: str = "stock"  # "stock" | "etf" | "reit" | "other"


@dataclass
class MarketFinancialData:
    """外部APIから取得した財務データ"""

    code: str
    fiscal_year: int
    bps: Decimal
    eps: Decimal | None = None
    roe: Decimal | None = None
    net_assets: int | None = None
    total_shares: int | None = None
    revenue: int | None = None
    operating_income: int | None = None
    eps_forecast: Decimal | None = None
    period_end_date: date | None = None  # J-Quants CurPerEn: 決算期末日（株式分割調整の基準日）
    operating_cash_flow: int | None = None  # 営業CF（百万円）
    free_cash_flow: int | None = None  # FCF（百万円）


@dataclass
class MarketPriceData:
    """外部APIから取得した株価データ"""

    code: str
    date: date
    close_price: Decimal
    volume: int | None = None
    adj_factor: Decimal = Decimal("1")  # 株式分割等の権利調整係数（J-Quants AdjFactor）
    is_limit_up: bool = False  # J-Quants UL: 日通ストップ高
    is_limit_down: bool = False  # J-Quants LL: 日通ストップ安


@dataclass
class MarketDividendData:
    """外部APIから取得した配当・分配金データ"""

    code: str
    ex_dividend_date: date
    dividends_per_share: Decimal
    record_date: date | None = None
    payable_date: date | None = None


@dataclass
class MarketMarginData:
    """外部APIから取得した信用取引残高データ"""

    code: str
    date: date
    long_balance: int | None = None  # 信用買残（株数）
    long_balance_change: int | None = None  # 信用買残変化
    short_balance: int | None = None  # 信用売残（株数）
    short_balance_change: int | None = None  # 信用売残変化
    sl_ratio: Decimal | None = None  # 信売比率（売残÷買残）


# ============================================================
# 外部データプロバイダーインターフェース
# ============================================================


class MarketDataProvider(ABC):
    """市場データプロバイダーインターフェース"""

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を返す（例: 'jquants', 'yfinance'）"""
        ...

    @abstractmethod
    def fetch_stock_list(self) -> list[MarketStockData]:
        """銘柄一覧を取得"""
        ...

    @abstractmethod
    def fetch_financials(self, code: str, fiscal_year: int | None = None) -> list[MarketFinancialData]:
        """財務データを取得"""
        ...

    @abstractmethod
    def fetch_prices(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketPriceData]:
        """株価データを取得"""
        ...

    def supports_bulk_fetch(self) -> bool:
        """一括取得（日付ベースで全銘柄）に対応しているか"""
        return False

    def fetch_all_prices(self, target_date: date) -> list[MarketPriceData]:
        """指定日の全銘柄株価を一括取得"""
        raise NotImplementedError

    def fetch_all_financials(self, from_date: date, to_date: date) -> list[MarketFinancialData]:
        """期間内の全銘柄財務データを一括取得"""
        raise NotImplementedError

    def fetch_dividends(self, code: str) -> list[MarketDividendData]:
        """配当・分配金履歴を取得。未対応プランは空リストを返す。"""
        return []

    def supports_dividend_fetch(self) -> bool:
        """配当データ取得に対応しているか"""
        return False

    def fetch_margin_balance(
        self,
        code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketMarginData]:
        """信用取引残高を取得。未対応プロバイダーは空リストを返す。"""
        return []

    def fetch_all_margin_balance(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MarketMarginData]:
        """全銘柄の信用取引残高を一括取得。未対応プロバイダーは空リストを返す。"""
        return []

    def supports_margin_fetch(self) -> bool:
        """信用残高データ取得に対応しているか"""
        return False


# ============================================================
# リポジトリインターフェース
# ============================================================


class StockRepository(ABC):
    """銘柄リポジトリインターフェース"""

    @abstractmethod
    def find_by_code(self, code: str) -> StockEntity | None: ...

    @abstractmethod
    def find_by_id(self, stock_id: int) -> StockEntity | None: ...

    @abstractmethod
    def list_all(self) -> list[StockEntity]: ...

    @abstractmethod
    def find_by_market_type(self, market_type: str, active_only: bool = True) -> list[StockEntity]: ...

    @abstractmethod
    def search_by_name(
        self,
        query: str,
        *,
        instrument_type: str | None = None,
        market_type: str | None = None,
        limit: int = 10,
    ) -> list[StockEntity]:
        """会社名・コードで曖昧検索する。

        - query は NFKC 正規化済みの前提（呼び出し側で正規化）
        - name に query を部分一致（大文字小文字無視）または code に完全一致
        - is_active=True のみ
        - instrument_type / market_type 指定時はそれらでも絞り込む
        - 並びは code 昇順、limit 件まで
        """
        ...

    @abstractmethod
    def deactivate_missing(self, market_type: str, active_codes: set[str]) -> int:
        """指定市場で active_codes に含まれない銘柄を is_active=False にする。"""
        ...

    @abstractmethod
    def save(self, entity: StockEntity) -> StockEntity: ...

    @abstractmethod
    def upsert(self, entity: StockEntity) -> StockEntity:
        """codeで検索し、存在すればupdate、なければcreate"""
        ...

    @abstractmethod
    def delete(self, stock_id: int) -> None: ...

    @abstractmethod
    def bulk_update_latest_prices(self, updates: Sequence[tuple[int, Decimal, date]]) -> None:
        """最新株価を一括更新。updates: [(stock_id, price, price_date), ...]"""
        ...


class FinancialRepository(ABC):
    """財務データリポジトリインターフェース"""

    @abstractmethod
    def find_by_stock_id(self, stock_id: int) -> list[FinancialEntity]: ...

    @abstractmethod
    def find_latest_by_stock_id(self, stock_id: int) -> FinancialEntity | None: ...

    @abstractmethod
    def find_recent_by_stock_id(self, stock_id: int, limit: int = 4) -> list[FinancialEntity]:
        """最新N件の財務データを年度降順で返す（成長率計算用）。"""
        ...

    def find_all_latest(self) -> dict[int, FinancialEntity]:
        """全銘柄の最新財務データを一括取得。{stock_id: entity}"""
        raise NotImplementedError

    def find_all_recent(self, limit: int = 4) -> dict[int, list[FinancialEntity]]:
        """全銘柄の直近N件の財務データを一括取得。{stock_id: [entities]}"""
        raise NotImplementedError

    def find_by_stock_ids(self, stock_ids: Sequence[int]) -> dict[int, list[FinancialEntity]]:
        """指定銘柄の全財務データを一括取得。{stock_id: [entities]} (fiscal_year DESC)"""
        raise NotImplementedError

    @abstractmethod
    def save(self, entity: FinancialEntity) -> FinancialEntity: ...

    @abstractmethod
    def bulk_save(self, entities: list[FinancialEntity]) -> list[FinancialEntity]: ...


class PriceRepository(ABC):
    """株価リポジトリインターフェース"""

    @abstractmethod
    def find_by_stock_id(self, stock_id: int, limit: int = 100) -> list[PriceEntity]: ...

    @abstractmethod
    def find_latest_by_stock_id(self, stock_id: int) -> PriceEntity | None: ...

    @abstractmethod
    def find_latest_date_by_stock_id(self, stock_id: int) -> str | None:
        """最新の株価日付を取得（増分同期用）"""
        ...

    @abstractmethod
    def save(self, entity: PriceEntity) -> PriceEntity: ...

    @abstractmethod
    def bulk_save(self, entities: list[PriceEntity]) -> list[PriceEntity]: ...

    @abstractmethod
    def find_price_near_date(self, stock_id: int, target_date: date) -> Decimal | None:
        """指定日に最も近い株価（前後7日以内）を返す。52週リターン計算用。"""
        ...

    @abstractmethod
    def find_52w_high_low(self, stock_id: int) -> tuple[Decimal, Decimal] | None:
        """直近52週の最高値・最安値を返す。データなしは None。"""
        ...

    @abstractmethod
    def find_all_52w_high_low(self) -> dict[int, tuple[Decimal, Decimal]]:
        """全銘柄の直近52週の最高値・最安値を一括取得。{stock_id: (high, low)}"""
        ...

    @abstractmethod
    def find_all_recent_prices(self, limit: int = 25) -> dict[int, list[PriceEntity]]:
        """全銘柄の直近N日の株価を一括取得。{stock_id: [PriceEntity, ...]}（日付降順）"""
        ...


class DividendRepository(ABC):
    """配当・分配金リポジトリインターフェース"""

    @abstractmethod
    def bulk_save(self, entities: list[DividendEntity]) -> None: ...

    @abstractmethod
    def find_by_stock_id(self, stock_id: int, limit: int = 20) -> list[DividendEntity]: ...

    @abstractmethod
    def find_annual_total(self, stock_id: int) -> Decimal | None:
        """直近12ヶ月の配当/分配金合計を返す。データなしは None。"""
        ...

    @abstractmethod
    def find_all_annual_totals(self, stock_ids: list[int]) -> dict[int, Decimal]:
        """複数銘柄の直近12ヶ月配当合計を一括取得。{stock_id: total}"""
        ...

    @abstractmethod
    def find_all_by_stock_ids(self, stock_ids: list[int]) -> dict[int, list[DividendEntity]]:
        """複数銘柄の全配当履歴を一括取得。{stock_id: [DividendEntity, ...]}（日付降順）"""
        ...

    def find_upcoming_by_stock_ids(
        self,
        stock_ids: list[int],
        *,
        from_date: date,
        to_date: date,
    ) -> list[DividendEntity]:
        """指定銘柄群の今後の配当予定（ex_dividend_date が [from_date, to_date] 範囲）を返す。

        並びは ex_dividend_date 昇順。空 stock_ids なら [] を返す。
        実装側で必要に応じて n+1 を避ける効率実装を行う。
        """
        raise NotImplementedError


class MarginRepository(ABC):
    """信用取引残高リポジトリインターフェース"""

    @abstractmethod
    def find_latest_by_stock_id(self, stock_id: int) -> MarginBalanceEntity | None: ...

    @abstractmethod
    def find_recent_by_stock_id(self, stock_id: int, limit: int = 8) -> list[MarginBalanceEntity]: ...

    def find_all_latest(self) -> dict[int, MarginBalanceEntity]:
        """全銘柄の最新信用残高を一括取得。{stock_id: entity}"""
        raise NotImplementedError

    @abstractmethod
    def bulk_save(self, data_list: list[MarketMarginData], stock_map: dict[str, int]) -> int:
        """信用残高データを一括保存。戻り値: 保存件数"""
        ...


class DailyMoversRepository(ABC):
    """日次急騰急落集計リポジトリインターフェース"""

    @abstractmethod
    def find_latest_date(self) -> date | None:
        """t_daily_movers の最新日付を返す。空なら None。"""

    @abstractmethod
    def find_by_date(self, target_date: date) -> list[DailyMoversEntity]:
        """指定日の全 movers を返す（並びは change_pct DESC が望ましいが呼び出し側でソート可）。"""

    @abstractmethod
    def find_by_date_and_stock_ids(
        self,
        target_date: date,
        stock_ids: list[int],
    ) -> list[DailyMoversEntity]:
        """指定日 × 銘柄群の movers を返す。"""

    @abstractmethod
    def bulk_replace(self, target_date: date, entities: list[DailyMoversEntity]) -> int:
        """target_date の既存行を削除し、entities を bulk_create する。戻り値: 保存件数。"""


class ApiConfigRepository(ABC):
    """API設定リポジトリインターフェース"""

    @abstractmethod
    def find_by_provider(self, provider: str) -> ApiConfigEntity | None: ...

    @abstractmethod
    def save(self, entity: ApiConfigEntity) -> ApiConfigEntity: ...


class SyncLogRepository(ABC):
    """同期ログリポジトリインターフェース"""

    @abstractmethod
    def save(self, entity: SyncLogEntity) -> SyncLogEntity: ...

    @abstractmethod
    def find_latest_by_type(self, sync_type: str, market: str) -> SyncLogEntity | None: ...

    @abstractmethod
    def list_recent(self, limit: int = 20) -> list[SyncLogEntity]: ...


class OwnerShareholderRepository(ABC):
    """オーナー経営指標（代表者-大株主紐付け）リポジトリ"""

    @abstractmethod
    def find_by_stock_id(self, stock_id: int) -> list[OwnerShareholderEntity]: ...

    @abstractmethod
    def find_latest_by_stock_ids(self, stock_ids: list[int]) -> dict[int, list[OwnerShareholderEntity]]:
        """複数銘柄の最新年度データを一括取得。{stock_id: [OwnerShareholderEntity, ...]}"""
        ...

    @abstractmethod
    def save_batch(self, stock_id: int, fiscal_year: int, entities: list[OwnerShareholderEntity]) -> None:
        """指定銘柄・年度のデータを置換保存。"""
        ...


class ShareholderRawRepository(ABC):
    """大株主生データリポジトリ"""

    @abstractmethod
    def save_batch(self, stock_id: int, fiscal_year: int, entities: list[ShareholderRawEntity]) -> None: ...

    @abstractmethod
    def find_by_stock_id(self, stock_id: int) -> list[ShareholderRawEntity]: ...


class ScreeningPresetRepository(ABC):
    """スクリーニングプリセットリポジトリ"""

    @abstractmethod
    def find_by_user_id(self, user_id: int) -> list[ScreeningPresetEntity]: ...

    @abstractmethod
    def find_by_id(self, preset_id: int, user_id: int) -> ScreeningPresetEntity | None: ...

    @abstractmethod
    def save(self, entity: ScreeningPresetEntity) -> ScreeningPresetEntity: ...

    @abstractmethod
    def delete(self, preset_id: int, user_id: int) -> bool: ...
