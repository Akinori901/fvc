"""口座スナップショット群を最新株価で動的に再評価するサービス。

CSV取り込み時点の静的値（AccountSnapshot.total_value_jpy）ではなく、
現時点の株価（StockPrice / Stock.latest_price）で各口座を再評価し、
家族合計・メンバー別合計・資産クラス別合計などを算出する。

計算ルール:
- 現物株: qty × latest_price
- 信用株: qty × latest_price - cost  （評価損益のみ計上）
- 投信プロキシ: snap_value × (cur_price / ref_price)  （ref_price = snapshot_date 時点の代理銘柄価格）
- 株式以外（現金等）: snap_value をそのまま計上（non_stock_value）

通貨換算: 米株（market_type='US'）の price は USD のまま DB に保存されているため、
評価日の USD/JPY を掛けて JPY に正規化してから集計する。
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from apps.portfolios.domain.entities import (
        AccountSnapshotEntity,
        PortfolioAccountEntity,
    )


class StockPriceSource(Protocol):
    """株価取得の依存性インターフェース。テスト時にモック注入可能にするため。"""

    def fetch_price_history(
        self, stock_ids: set[int], from_date: datetime.date, to_date: datetime.date
    ) -> dict[int, dict[str, Decimal]]:
        """stock_ids について from_date 〜 to_date の終値を取得。

        戻り値: {stock_id: {date_str: close_price}}
        """
        ...

    def fetch_latest_prices(self, stock_ids: set[int]) -> dict[int, Decimal]:
        """stock_ids について latest_price を取得。

        戻り値: {stock_id: latest_price}（latest_price が None の銘柄は含まない）
        """
        ...

    def fetch_market_types(self, stock_ids: set[int]) -> dict[int, str]:
        """stock_ids について market_type を取得。

        戻り値: {stock_id: market_type}  例: 'JP', 'US'
        """
        ...


class CurrencyConverter(Protocol):
    """日付ごとの USD→JPY 換算レート供給。"""

    def get_rate(self, target_date: datetime.date | str) -> Decimal | None: ...


class DjangoStockPriceSource:
    """Django ORM 経由の StockPriceSource 実装。"""

    def fetch_price_history(
        self, stock_ids: set[int], from_date: datetime.date, to_date: datetime.date
    ) -> dict[int, dict[str, Decimal]]:
        from apps.stocks.models import StockPrice

        result: dict[int, dict[str, Decimal]] = {}
        if not stock_ids:
            return result
        for sid, price_date, price in StockPrice.objects.filter(
            stock_id__in=stock_ids,
            date__gte=from_date,
            date__lte=to_date,
        ).values_list("stock_id", "date", "close_price"):
            result.setdefault(sid, {})[str(price_date)] = price
        return result

    def fetch_latest_prices(self, stock_ids: set[int]) -> dict[int, Decimal]:
        from apps.stocks.models import Stock

        result: dict[int, Decimal] = {}
        if not stock_ids:
            return result
        for stk in Stock.objects.filter(pk__in=stock_ids).only("id", "latest_price"):
            if stk.latest_price is not None:
                result[stk.pk] = stk.latest_price
        return result

    def fetch_market_types(self, stock_ids: set[int]) -> dict[int, str]:
        from apps.stocks.models import Stock

        result: dict[int, str] = {}
        if not stock_ids:
            return result
        for stk in Stock.objects.filter(pk__in=stock_ids).only("id", "market_type"):
            result[stk.pk] = stk.market_type
        return result


@dataclass(frozen=True)
class DynamicValuationInput:
    """動的評価サービスへの入力。"""

    accounts: list[PortfolioAccountEntity]
    """スコープ内の口座一覧。"""

    snapshots: list[AccountSnapshotEntity]
    """各口座の最新スナップショット。account_id が accounts に含まれないものは無視される。"""

    as_of_date: datetime.date
    """評価基準日（通常は today）。"""


@dataclass
class DynamicValuationResult:
    """動的評価サービスの出力。

    Decimal を返し、int/str への変換は呼び出し側の責務とする。
    """

    total_value: Decimal = Decimal(0)
    by_asset_class: dict[str, Decimal] = field(default_factory=dict)
    by_account: dict[int, Decimal] = field(default_factory=dict)
    by_member: dict[int, Decimal] = field(default_factory=dict)
    by_member_asset_class: dict[int, dict[str, Decimal]] = field(default_factory=dict)
    non_stock_value: Decimal = Decimal(0)
    stock_total: Decimal = Decimal(0)
    stock_price_map: dict[int, Decimal] = field(default_factory=dict)
    """stock_id → latest_price。呼び出し側でクエリを再利用するために expose。"""


class DynamicPortfolioValuationService:
    """最新株価で口座群を再評価する。

    Single Responsibility: 評価額の再計算のみ。
    集計ループや表示整形は呼び出し側の責務。
    """

    def __init__(
        self,
        price_source: StockPriceSource | None = None,
        currency_converter: CurrencyConverter | None = None,
    ) -> None:
        self._price_source: StockPriceSource = price_source or DjangoStockPriceSource()
        if currency_converter is None:
            from .fx_conversion_service import FxConversionService

            currency_converter = FxConversionService()
        self._fx: CurrencyConverter = currency_converter

    def evaluate(self, input_: DynamicValuationInput) -> DynamicValuationResult:
        accounts_by_id: dict[int, PortfolioAccountEntity] = {a.id: a for a in input_.accounts if a.id is not None}
        account_ids = set(accounts_by_id.keys())
        scope_snapshots = [s for s in input_.snapshots if s.account_id in account_ids]

        if not scope_snapshots:
            return DynamicValuationResult()

        # ── holding を分類 ──
        spot_holdings, margin_holdings, fund_holdings, classification = self._classify_all(
            scope_snapshots, accounts_by_id
        )

        # ── 口座の固定部分（現金等）を算出 ──
        non_stock_by_account = self._compute_non_stock_parts(scope_snapshots, accounts_by_id, classification)

        # ── 株価一括取得 ──
        all_stock_ids = (
            {sid for sid, _, _ in spot_holdings}
            | {sid for sid, _, _, _ in margin_holdings}
            | {sid for sid, _, _, _ in fund_holdings}
        )
        price_map, latest_price_map = self._fetch_prices(all_stock_ids, input_.as_of_date, fund_holdings)
        market_type_map = self._price_source.fetch_market_types(all_stock_ids)

        def get_price(stock_id: int, date_str: str) -> Decimal | None:
            """株価取得（前方補完あり、最終フォールバック = latest_price）。市場通貨のまま。"""
            prices = price_map.get(stock_id, {})
            price = prices.get(date_str)
            if price is None:
                earlier = [d for d in prices if d <= date_str]
                price = prices[max(earlier)] if earlier else latest_price_map.get(stock_id)
            return price

        def get_price_jpy(stock_id: int, date_str: str) -> Decimal | None:
            """株価取得後、米株なら指定日の USD/JPY で JPY に正規化して返す。"""
            price = get_price(stock_id, date_str)
            if price is None:
                return None
            if market_type_map.get(stock_id) == "US":
                rate = self._fx.get_rate(date_str)
                if rate is None:
                    # 為替取得不可: 米株は集計から除外（None 扱い）
                    return None
                return price * rate
            return price

        # ── 動的評価 ──
        as_of_str = str(input_.as_of_date)
        dynamic_stock_by_account: dict[int, Decimal] = {}

        for sid, qty, acc_id in spot_holdings:
            price_jpy = get_price_jpy(sid, as_of_str)
            if price_jpy is not None:
                dynamic_stock_by_account[acc_id] = dynamic_stock_by_account.get(acc_id, Decimal(0)) + qty * price_jpy

        for sid, qty, cost, acc_id in margin_holdings:
            price_jpy = get_price_jpy(sid, as_of_str)
            if price_jpy is not None:
                pnl = qty * price_jpy - cost
                dynamic_stock_by_account[acc_id] = dynamic_stock_by_account.get(acc_id, Decimal(0)) + pnl

        for proxy_id, snap_value, snap_date, acc_id in fund_holdings:
            # 投信プロキシは比率計算なので通貨非依存（市場通貨のままで OK）
            ref_price = get_price(proxy_id, snap_date)
            cur_price = get_price(proxy_id, as_of_str)
            value = (
                snap_value * (cur_price / ref_price)
                if ref_price and cur_price and ref_price > 0
                else snap_value  # フォールバック: 取得時点の値
            )
            dynamic_stock_by_account[acc_id] = dynamic_stock_by_account.get(acc_id, Decimal(0)) + value

        # ── 集計 ──
        result = DynamicValuationResult()
        result.stock_price_map = latest_price_map.copy()

        for acc_id, acc in accounts_by_id.items():
            stock_part = dynamic_stock_by_account.get(acc_id, Decimal(0))
            non_stock_part = non_stock_by_account.get(acc_id, Decimal(0))
            account_total = stock_part + non_stock_part

            result.by_account[acc_id] = account_total
            result.total_value += account_total
            result.stock_total += stock_part
            result.non_stock_value += non_stock_part

            cls = acc.asset_class
            result.by_asset_class[cls] = result.by_asset_class.get(cls, Decimal(0)) + account_total

            m_id = acc.family_member_id
            result.by_member[m_id] = result.by_member.get(m_id, Decimal(0)) + account_total
            mbc = result.by_member_asset_class.setdefault(m_id, {})
            mbc[cls] = mbc.get(cls, Decimal(0)) + account_total

        return result

    # ── 内部ヘルパー（純粋関数） ──

    @staticmethod
    def _classify_all(
        scope_snapshots: list[AccountSnapshotEntity],
        accounts_by_id: dict[int, PortfolioAccountEntity],
    ) -> tuple[
        list[tuple[int, Decimal, int]],
        list[tuple[int, Decimal, Decimal, int]],
        list[tuple[int, Decimal, str, int]],
        dict[str, dict[int, Decimal]],
    ]:
        """全 holdings を spot/margin/fund に分類し、口座別の補助集計も返す。

        戻り値:
            spot_holdings: [(stock_id, qty, account_id)]
            margin_holdings: [(stock_id, qty, cost, account_id)]
            fund_holdings: [(proxy_stock_id, snap_value, snap_date, account_id)]
            classification: 補助集計（key: spot_stock / margin_pnl_snap）
        """
        spot_holdings: list[tuple[int, Decimal, int]] = []
        margin_holdings: list[tuple[int, Decimal, Decimal, int]] = []
        fund_holdings: list[tuple[int, Decimal, str, int]] = []
        spot_stock_value_by_account: dict[int, Decimal] = {}
        margin_pnl_snapshot_by_account: dict[int, Decimal] = {}

        for snap in scope_snapshots:
            acc = accounts_by_id.get(snap.account_id)
            if acc is None:
                continue
            is_margin = acc.trading_type == "margin"
            for h in snap.holdings:
                if is_margin:
                    if h.stock_id is not None and h.quantity is not None and h.quantity > 0:
                        cost = h.cost_jpy if h.cost_jpy is not None else Decimal(0)
                        margin_holdings.append((h.stock_id, h.quantity, cost, snap.account_id))
                        margin_pnl_snapshot_by_account[snap.account_id] = margin_pnl_snapshot_by_account.get(
                            snap.account_id, Decimal(0)
                        ) + (h.value_jpy - cost)
                else:
                    if h.stock_id is not None and h.quantity is not None and h.quantity > 0:
                        spot_holdings.append((h.stock_id, h.quantity, snap.account_id))
                        spot_stock_value_by_account[snap.account_id] = (
                            spot_stock_value_by_account.get(snap.account_id, Decimal(0)) + h.value_jpy
                        )
                    elif h.proxy_stock_id is not None:
                        fund_holdings.append((h.proxy_stock_id, h.value_jpy, snap.snapshot_date, snap.account_id))
                        spot_stock_value_by_account[snap.account_id] = (
                            spot_stock_value_by_account.get(snap.account_id, Decimal(0)) + h.value_jpy
                        )

        return (
            spot_holdings,
            margin_holdings,
            fund_holdings,
            {
                "spot_stock": spot_stock_value_by_account,
                "margin_pnl_snap": margin_pnl_snapshot_by_account,
            },
        )

    @staticmethod
    def _compute_non_stock_parts(
        scope_snapshots: list[AccountSnapshotEntity],
        accounts_by_id: dict[int, PortfolioAccountEntity],
        classification: dict[str, dict[int, Decimal]],
    ) -> dict[int, Decimal]:
        """口座ごとの株式以外の固定部分（現金等）を算出する。"""
        result: dict[int, Decimal] = {}
        spot_stock_value_by_account = classification["spot_stock"]
        margin_pnl_snapshot_by_account = classification["margin_pnl_snap"]

        for snap in scope_snapshots:
            acc = accounts_by_id.get(snap.account_id)
            if acc is None:
                continue
            is_margin = acc.trading_type == "margin"
            val = snap.total_value_jpy
            cost = snap.total_cost_jpy
            effective = ((val - cost) if cost is not None else Decimal(0)) if is_margin else val

            if is_margin:
                margin_pnl_snap = margin_pnl_snapshot_by_account.get(snap.account_id, Decimal(0))
                result[snap.account_id] = effective - margin_pnl_snap
            else:
                stock_val_in_acc = spot_stock_value_by_account.get(snap.account_id, Decimal(0))
                result[snap.account_id] = effective - stock_val_in_acc

        return result

    def _fetch_prices(
        self,
        stock_ids: set[int],
        as_of_date: datetime.date,
        fund_holdings: list[tuple[int, Decimal, str, int]],
    ) -> tuple[dict[int, dict[str, Decimal]], dict[int, Decimal]]:
        """株価を一括取得する（履歴 + 最新）。"""
        if not stock_ids:
            return {}, {}

        month_start = as_of_date.replace(day=1)
        from_date = month_start - datetime.timedelta(days=40)

        # fund 系の最古スナップショット日も含むよう余裕を持たせる
        fund_snap_dates = [d for _, _, d, _ in fund_holdings]
        if fund_snap_dates:
            try:
                oldest_fund_date = datetime.date.fromisoformat(min(fund_snap_dates))
                from_date = min(from_date, oldest_fund_date - datetime.timedelta(days=10))
            except ValueError:
                pass  # 不正な日付フォーマットは無視

        price_map = self._price_source.fetch_price_history(stock_ids, from_date, as_of_date)
        latest_price_map = self._price_source.fetch_latest_prices(stock_ids)
        return price_map, latest_price_map
