"""DynamicPortfolioValuationService 単体テスト（DBアクセスなし）。"""

from __future__ import annotations

import datetime
from decimal import Decimal

from apps.portfolios.application.services.dynamic_valuation_service import (
    DynamicPortfolioValuationService,
    DynamicValuationInput,
    StockPriceSource,
)
from apps.portfolios.domain.entities import (
    AccountHoldingEntity,
    AccountSnapshotEntity,
    PortfolioAccountEntity,
)


class _FakePriceSource(StockPriceSource):
    """テスト用のインメモリ StockPriceSource。"""

    def __init__(
        self,
        history: dict[int, dict[str, Decimal]] | None = None,
        latest: dict[int, Decimal] | None = None,
        market_types: dict[int, str] | None = None,
    ) -> None:
        self.history = history or {}
        self.latest = latest or {}
        # 既存テストの市場通貨を JPY 前提に保つため、明示指定なき場合は全銘柄を "JP" 扱い
        self.market_types = market_types or {}
        self.fetch_history_calls = 0
        self.fetch_latest_calls = 0

    def fetch_price_history(
        self,
        stock_ids: set[int],
        from_date: datetime.date,  # noqa: ARG002
        to_date: datetime.date,  # noqa: ARG002
    ) -> dict[int, dict[str, Decimal]]:
        self.fetch_history_calls += 1
        return {sid: self.history.get(sid, {}) for sid in stock_ids if sid in self.history}

    def fetch_latest_prices(self, stock_ids: set[int]) -> dict[int, Decimal]:
        self.fetch_latest_calls += 1
        return {sid: self.latest[sid] for sid in stock_ids if sid in self.latest}

    def fetch_market_types(self, stock_ids: set[int]) -> dict[int, str]:
        return {sid: self.market_types.get(sid, "JP") for sid in stock_ids}


class _FakeFxConverter:
    """テスト用の固定レート FX 換算。"""

    def __init__(self, rate: Decimal | None = Decimal("150")) -> None:
        self.rate = rate
        self.calls: list[str] = []

    def get_rate(self, target_date: datetime.date | str) -> Decimal | None:
        self.calls.append(target_date if isinstance(target_date, str) else str(target_date))
        return self.rate


def _make_account(
    acc_id: int,
    member_id: int,
    *,
    asset_class: str = "jp_stock",
    trading_type: str = "spot",
) -> PortfolioAccountEntity:
    return PortfolioAccountEntity(
        id=acc_id,
        family_member_id=member_id,
        institution="test",
        institution_type="securities_jp",
        asset_class=asset_class,
        trading_type=trading_type,
    )


def _make_snapshot(
    acc_id: int,
    snapshot_date: str,
    total_value: Decimal,
    holdings: list[AccountHoldingEntity],
    *,
    total_cost: Decimal | None = None,
) -> AccountSnapshotEntity:
    return AccountSnapshotEntity(
        id=None,
        account_id=acc_id,
        snapshot_date=snapshot_date,
        total_value_jpy=total_value,
        total_cost_jpy=total_cost,
        holdings=holdings,
    )


def _make_holding(
    *,
    asset_name: str = "テスト",
    asset_type: str = "stock",
    value_jpy: Decimal,
    stock_id: int | None = None,
    proxy_stock_id: int | None = None,
    quantity: Decimal | None = None,
    cost_jpy: Decimal | None = None,
) -> AccountHoldingEntity:
    return AccountHoldingEntity(
        id=None,
        snapshot_id=0,
        asset_name=asset_name,
        asset_type=asset_type,
        value_jpy=value_jpy,
        stock_id=stock_id,
        proxy_stock_id=proxy_stock_id,
        quantity=quantity,
        cost_jpy=cost_jpy,
    )


AS_OF = datetime.date(2026, 5, 9)


class TestDynamicPortfolioValuationServiceSpot:
    """現物口座のテスト。"""

    def test_simple_spot_holding_uses_latest_price(self) -> None:
        # スナップショット時点: qty=10 × 1000 = 10000
        # 最新株価: 1500 → 動的評価 = 15000
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                )
            ],
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("15000")
        assert result.stock_total == Decimal("15000")
        assert result.non_stock_value == Decimal("0")
        assert result.by_account == {1: Decimal("15000")}
        assert result.by_member == {1: Decimal("15000")}
        assert result.by_asset_class == {"jp_stock": Decimal("15000")}

    def test_spot_with_cash_balance_keeps_cash_static(self) -> None:
        # snapshot total=15000 = 株式 10000 + 現金 5000
        # 株式が 15000 に値上がり → 動的合計 20000
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("15000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                )
            ],
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("20000")
        assert result.stock_total == Decimal("15000")
        assert result.non_stock_value == Decimal("5000")

    def test_spot_with_no_latest_price_uses_history_then_falls_back(self) -> None:
        # latest_price なし、history も空 → 当該銘柄は 0 加算
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                )
            ],
        )
        source = _FakePriceSource()
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 株式部分は 0、現金部分は total - value_jpy = 0
        assert result.total_value == Decimal("0")

    def test_zero_quantity_holding_is_skipped(self) -> None:
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("0"),
            [
                _make_holding(
                    value_jpy=Decimal("0"),
                    stock_id=100,
                    quantity=Decimal("0"),
                )
            ],
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("0")


class TestDynamicPortfolioValuationServiceMargin:
    """信用口座のテスト（評価損益のみ計上）。"""

    def test_margin_pnl_uses_latest_price(self) -> None:
        # qty=10, price=1500, cost=10000 → pnl = 5000
        # snapshot: total=10000, cost=8000 → effective = 2000（pnl_snap）
        # 信用口座は effective が固定（non_stock 扱い）→ 0 になる
        # 動的pnl 5000 + non_stock (effective - margin_pnl_snap = 2000 - 2000 = 0) = 5000
        acc = _make_account(1, 1, trading_type="margin")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                    cost_jpy=Decimal("8000"),
                )
            ],
            total_cost=Decimal("8000"),
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 動的 pnl = 10 × 1500 - 8000 = 7000
        assert result.total_value == Decimal("7000")

    def test_margin_with_loss(self) -> None:
        # qty=10, price=700, cost=8000 → pnl = -1000（含み損）
        acc = _make_account(1, 1, trading_type="margin")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("8000"),
            [
                _make_holding(
                    value_jpy=Decimal("8000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                    cost_jpy=Decimal("8000"),
                )
            ],
            total_cost=Decimal("8000"),
        )
        source = _FakePriceSource(latest={100: Decimal("700")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("-1000")

    def test_margin_with_none_cost_treats_as_zero_cost(self) -> None:
        # holding cost が None → 0 として扱われる（保守的）
        # 動的 pnl = 10 × 1500 - 0 = 15000
        # snap 時点: pnl_snap = value_jpy - 0 = 10000 → effective(total_cost=None) = 0
        #   → non_stock = 0 - 10000 = -10000（この口座の見えない信用枠の調整分）
        # 合計 = 15000 + (-10000) = 5000（snap 時点 0 円から +5000 値上がり）
        acc = _make_account(1, 1, trading_type="margin")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                    cost_jpy=None,
                )
            ],
            total_cost=None,
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("5000")


class TestDynamicPortfolioValuationServiceFund:
    """投信プロキシのテスト（変動率近似）。"""

    def test_fund_proxy_uses_ratio(self) -> None:
        # snap_value=100000, ref=10000, cur=11000 → 110000
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("100000"),
            [
                _make_holding(
                    value_jpy=Decimal("100000"),
                    proxy_stock_id=200,
                )
            ],
        )
        source = _FakePriceSource(
            history={
                200: {"2026-05-01": Decimal("10000"), "2026-05-09": Decimal("11000")},
            },
            latest={200: Decimal("11000")},
        )
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        assert result.total_value == Decimal("110000")

    def test_fund_proxy_falls_back_to_static_when_ref_missing(self) -> None:
        # ref_price 取得不可 → snap_value をそのまま使う
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("100000"),
            [
                _make_holding(
                    value_jpy=Decimal("100000"),
                    proxy_stock_id=200,
                )
            ],
        )
        source = _FakePriceSource(latest={200: Decimal("11000")})  # history なし、latest はあるが ref で使えない
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # ref_price は latest にフォールバック、cur_price も latest → ref/cur が同値 → snap_value のまま
        assert result.total_value == Decimal("100000")


class TestDynamicPortfolioValuationServiceMultiple:
    """複数メンバー・口座・銘柄が混在するケース。"""

    def test_multi_member_aggregation(self) -> None:
        # member 1: 口座1（jp_stock, 株 qty=10@1500）
        # member 2: 口座2（cash, 現金 5000）
        # 家族合計: 15000 + 5000 = 20000
        acc1 = _make_account(1, 1)
        acc2 = _make_account(2, 2, asset_class="cash")
        snap1 = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                )
            ],
        )
        snap2 = _make_snapshot(2, "2026-05-01", Decimal("5000"), [])
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(
            DynamicValuationInput(
                accounts=[acc1, acc2],
                snapshots=[snap1, snap2],
                as_of_date=AS_OF,
            )
        )

        assert result.total_value == Decimal("20000")
        assert result.by_member == {1: Decimal("15000"), 2: Decimal("5000")}
        assert result.by_asset_class == {"jp_stock": Decimal("15000"), "cash": Decimal("5000")}
        assert result.by_member_asset_class == {
            1: {"jp_stock": Decimal("15000")},
            2: {"cash": Decimal("5000")},
        }

    def test_same_stock_in_multiple_accounts_aggregated_correctly(self) -> None:
        # 口座1: stock_id=100, qty=10  →  動的 15000
        # 口座2: stock_id=100, qty=20  →  動的 30000
        acc1 = _make_account(1, 1)
        acc2 = _make_account(2, 1)
        snap1 = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [
                _make_holding(
                    value_jpy=Decimal("10000"),
                    stock_id=100,
                    quantity=Decimal("10"),
                )
            ],
        )
        snap2 = _make_snapshot(
            2,
            "2026-05-01",
            Decimal("20000"),
            [
                _make_holding(
                    value_jpy=Decimal("20000"),
                    stock_id=100,
                    quantity=Decimal("20"),
                )
            ],
        )
        source = _FakePriceSource(latest={100: Decimal("1500")})
        service = DynamicPortfolioValuationService(price_source=source)

        result = service.evaluate(
            DynamicValuationInput(
                accounts=[acc1, acc2],
                snapshots=[snap1, snap2],
                as_of_date=AS_OF,
            )
        )

        assert result.total_value == Decimal("45000")
        assert result.by_account == {1: Decimal("15000"), 2: Decimal("30000")}
        # クエリは1回ずつしか走らない（DI の price_source 経由）
        assert source.fetch_history_calls == 1
        assert source.fetch_latest_calls == 1

    def test_empty_input_returns_zero_result(self) -> None:
        service = DynamicPortfolioValuationService(price_source=_FakePriceSource())

        result = service.evaluate(DynamicValuationInput(accounts=[], snapshots=[], as_of_date=AS_OF))

        assert result.total_value == Decimal("0")
        assert result.by_member == {}

    def test_snapshot_for_unrelated_account_is_ignored(self) -> None:
        # accounts に含まれない口座のスナップショットは無視される
        acc1 = _make_account(1, 1)
        snap_other = _make_snapshot(
            999,
            "2026-05-01",
            Decimal("999999"),
            [],
        )
        service = DynamicPortfolioValuationService(price_source=_FakePriceSource())

        result = service.evaluate(
            DynamicValuationInput(
                accounts=[acc1],
                snapshots=[snap_other],
                as_of_date=AS_OF,
            )
        )

        assert result.total_value == Decimal("0")


class TestDynamicPortfolioValuationServiceCurrency:
    """米株 (market_type='US') の USD → JPY 換算テスト。

    Stock.latest_price / StockPrice.close_price は米株の場合 USD で保存されるため、
    評価日の USD/JPY を掛けて JPY に正規化する必要がある。
    """

    def test_us_stock_latest_price_is_converted_to_jpy(self) -> None:
        # NVDA 風: 20 株 × 220 USD × 150 JPY/USD = 660,000 JPY
        # スナップショットの value_jpy は楽天 CSV 由来の JPY 値 (= 685,610) で、
        # non_stock_value 計算には使われるが動的評価では再計算される。
        acc = _make_account(1, 1, asset_class="us_stock")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("685610"),  # CSV 由来の合計
            [
                _make_holding(
                    asset_name="NVDA",
                    value_jpy=Decimal("685610"),
                    stock_id=100,
                    quantity=Decimal("20"),
                )
            ],
        )
        source = _FakePriceSource(
            latest={100: Decimal("220")},  # 米株 latest_price は USD のまま
            market_types={100: "US"},
        )
        fx = _FakeFxConverter(rate=Decimal("150"))
        service = DynamicPortfolioValuationService(price_source=source, currency_converter=fx)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 株式部分 = 20 × 220 × 150 = 660,000
        # non_stock_part = total_value(685,610) - sum_value_jpy(685,610) = 0
        assert result.stock_total == Decimal("660000")
        assert result.total_value == Decimal("660000")
        assert fx.calls == [str(AS_OF)]

    def test_jp_stock_is_not_fx_converted(self) -> None:
        # 日本株は market_type='JP'。FX を掛けない（既存の挙動）。
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("10000"),
            [_make_holding(value_jpy=Decimal("10000"), stock_id=100, quantity=Decimal("10"))],
        )
        source = _FakePriceSource(latest={100: Decimal("1500")}, market_types={100: "JP"})
        fx = _FakeFxConverter(rate=Decimal("150"))
        service = DynamicPortfolioValuationService(price_source=source, currency_converter=fx)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 日本株は USD/JPY 不要 → 1500 をそのまま JPY として扱う
        assert result.stock_total == Decimal("15000")
        # FX 換算サービスは日本株では呼ばれない
        assert fx.calls == []

    def test_mixed_jp_and_us_holdings_in_same_account(self) -> None:
        # 日本株 と 米株 を同じ口座で混在保有
        acc = _make_account(1, 1)
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("100000"),
            [
                # 日本株: 10 株 × 取込時 1000 JPY = 10,000 JPY
                _make_holding(asset_name="JP", value_jpy=Decimal("10000"), stock_id=100, quantity=Decimal("10")),
                # 米株: 5 株 × 取込時 12,000 JPY = 60,000 JPY
                _make_holding(asset_name="US", value_jpy=Decimal("60000"), stock_id=200, quantity=Decimal("5")),
                # 残り 30,000 JPY は現金等
            ],
        )
        source = _FakePriceSource(
            latest={
                100: Decimal("1500"),  # JP: 1500 JPY
                200: Decimal("100"),  # US: 100 USD
            },
            market_types={100: "JP", 200: "US"},
        )
        fx = _FakeFxConverter(rate=Decimal("150"))
        service = DynamicPortfolioValuationService(price_source=source, currency_converter=fx)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 日本株: 10 × 1500 = 15,000
        # 米株: 5 × 100 × 150 = 75,000
        # 現金: 100,000 - (10,000 + 60,000) = 30,000
        # 合計: 15,000 + 75,000 + 30,000 = 120,000
        assert result.stock_total == Decimal("90000")
        assert result.non_stock_value == Decimal("30000")
        assert result.total_value == Decimal("120000")

    def test_us_stock_excluded_when_fx_rate_unavailable(self) -> None:
        # FX レート取得不可 (DB空 + ネット失敗) のとき、米株は集計から除外
        acc = _make_account(1, 1, asset_class="us_stock")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("100000"),
            [
                _make_holding(
                    asset_name="NVDA",
                    value_jpy=Decimal("100000"),
                    stock_id=200,
                    quantity=Decimal("10"),
                )
            ],
        )
        source = _FakePriceSource(latest={200: Decimal("100")}, market_types={200: "US"})
        fx = _FakeFxConverter(rate=None)  # FX 取得失敗
        service = DynamicPortfolioValuationService(price_source=source, currency_converter=fx)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 米株は除外 → stock_total = 0、non_stock = 100,000 - 100,000 = 0
        assert result.stock_total == Decimal("0")
        assert result.total_value == Decimal("0")

    def test_us_margin_stock_pnl_uses_jpy_normalized_price(self) -> None:
        # 米株の信用建玉。cost_jpy は CSV 取込時に JPY 換算済み。
        # 損益 = qty × price_jpy - cost_jpy
        acc = _make_account(1, 1, trading_type="margin", asset_class="us_stock")
        snap = _make_snapshot(
            1,
            "2026-05-01",
            Decimal("180000"),  # CSV 評価額
            [
                _make_holding(
                    asset_name="NVDA",
                    value_jpy=Decimal("180000"),
                    stock_id=200,
                    quantity=Decimal("10"),
                    cost_jpy=Decimal("150000"),
                )
            ],
            total_cost=Decimal("150000"),
        )
        source = _FakePriceSource(latest={200: Decimal("130")}, market_types={200: "US"})
        fx = _FakeFxConverter(rate=Decimal("150"))
        service = DynamicPortfolioValuationService(price_source=source, currency_converter=fx)

        result = service.evaluate(DynamicValuationInput(accounts=[acc], snapshots=[snap], as_of_date=AS_OF))

        # 損益 = 10 × 130 × 150 - 150,000 = 195,000 - 150,000 = 45,000
        assert result.stock_total == Decimal("45000")
