from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from ..domain.entities import (
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
from ..domain.repositories import (
    ApiConfigRepository,
    DailyMoversRepository,
    DividendRepository,
    FinancialRepository,
    MarginRepository,
    MarketMarginData,
    OwnerShareholderRepository,
    PriceRepository,
    ScreeningPresetRepository,
    ShareholderRawRepository,
    StockRepository,
    SyncLogRepository,
)
from ..domain.screening_preset import ScreeningPresetEntity
from ..models import (
    ApiConfig,
    DailyMovers,
    Dividend,
    FinancialManualInput,
    MarginBalance,
    OwnerShareholder,
    ScreeningPreset,
    ShareholderRaw,
    Stock,
    StockFinancial,
    StockPrice,
    SyncLog,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class DjangoStockRepository(StockRepository):
    """Django ORM による銘柄リポジトリ実装"""

    def _to_entity(self, obj: Stock) -> StockEntity:
        return StockEntity(
            id=obj.pk,
            code=obj.code,
            name=obj.name,
            market=obj.market,
            market_type=obj.market_type,
            instrument_type=obj.instrument_type,
            sector=obj.sector,
            is_active=obj.is_active_override if obj.is_active_override is not None else obj.is_active,
            is_active_override=obj.is_active_override,
            latest_price=obj.latest_price,
            latest_price_date=obj.latest_price_date,
        )

    def find_by_code(self, code: str) -> StockEntity | None:
        try:
            return self._to_entity(Stock.objects.get(code=code))
        except Stock.DoesNotExist:
            return None

    def find_by_id(self, stock_id: int) -> StockEntity | None:
        try:
            return self._to_entity(Stock.objects.get(pk=stock_id))
        except Stock.DoesNotExist:
            return None

    def list_all(self) -> list[StockEntity]:
        return [self._to_entity(obj) for obj in Stock.objects.all()]

    def find_by_market_type(self, market_type: str, active_only: bool = True) -> list[StockEntity]:
        qs = Stock.objects.filter(market_type=market_type)
        if active_only:
            qs = qs.filter(is_active=True)
        return [self._to_entity(obj) for obj in qs]

    def search_by_name(
        self,
        query: str,
        *,
        instrument_type: str | None = None,
        market_type: str | None = None,
        limit: int = 10,
    ) -> list[StockEntity]:
        from django.db.models import Q

        qs = Stock.objects.filter(is_active=True).filter(Q(name__icontains=query) | Q(code__iexact=query))
        if instrument_type:
            qs = qs.filter(instrument_type=instrument_type)
        if market_type:
            qs = qs.filter(market_type=market_type)
        qs = qs.order_by("code")[:limit]
        return [self._to_entity(obj) for obj in qs]

    # J-Quantsレスポンスに N回連続で含まれなかった銘柄を上場廃止とみなす閾値
    _DEACTIVATE_THRESHOLD = 3

    def deactivate_missing(self, market_type: str, active_codes: set[str]) -> int:
        """指定市場で active_codes に含まれない銘柄を連続欠損カウント後に廃止マークする。

        is_active_override が設定されている銘柄は対象外（手動オーバーライドを尊重）。
        3回連続でリストになければ is_active=False にする。
        """
        from django.db.models import F

        # オーバーライドなしの銘柄のみ対象
        base_qs = Stock.objects.filter(market_type=market_type, is_active_override__isnull=True)

        # 今回リストにある銘柄: カウンタリセット + is_active=True
        base_qs.filter(code__in=active_codes).update(
            consecutive_missing_syncs=0,
            is_active=True,
        )

        # 今回リストにない銘柄: カウンタをインクリメント
        base_qs.exclude(code__in=active_codes).update(
            consecutive_missing_syncs=F("consecutive_missing_syncs") + 1,
        )

        # 閾値以上の銘柄を廃止マーク
        deactivated = (
            base_qs.exclude(code__in=active_codes)
            .filter(
                consecutive_missing_syncs__gte=self._DEACTIVATE_THRESHOLD,
                is_active=True,
            )
            .update(is_active=False)
        )

        return deactivated

    def save(self, entity: StockEntity) -> StockEntity:
        if entity.id:
            Stock.objects.filter(pk=entity.id).update(
                code=entity.code,
                name=entity.name,
                market=entity.market,
                market_type=entity.market_type,
                sector=entity.sector,
                is_active=entity.is_active,
            )
            return entity
        obj = Stock.objects.create(
            code=entity.code,
            name=entity.name,
            market=entity.market,
            market_type=entity.market_type,
            sector=entity.sector,
            is_active=entity.is_active,
        )
        entity.id = obj.pk
        return entity

    def upsert(self, entity: StockEntity) -> StockEntity:
        obj, _ = Stock.objects.update_or_create(
            code=entity.code,
            defaults={
                "name": entity.name,
                "market": entity.market,
                "market_type": entity.market_type,
                "instrument_type": entity.instrument_type,
                "sector": entity.sector,
                "is_active": entity.is_active,
            },
        )
        entity.id = obj.pk
        return entity

    def delete(self, stock_id: int) -> None:
        Stock.objects.filter(pk=stock_id).delete()

    def bulk_update_latest_prices(self, updates: Sequence[tuple[int, Decimal, date]]) -> None:
        """最新株価を一括更新。updates: [(stock_id, price, price_date), ...]"""
        if not updates:
            return
        objs = Stock.objects.filter(pk__in=[u[0] for u in updates])
        obj_map = {obj.pk: obj for obj in objs}
        to_update = []
        for stock_id, price, price_date in updates:
            obj = obj_map.get(stock_id)
            if obj:
                obj.latest_price = price
                obj.latest_price_date = price_date
                to_update.append(obj)
        if to_update:
            Stock.objects.bulk_update(to_update, ["latest_price", "latest_price_date"])


class DjangoFinancialRepository(FinancialRepository):
    """Django ORM による財務データリポジトリ実装"""

    def _to_entity(self, obj: StockFinancial) -> FinancialEntity:
        return FinancialEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            fiscal_year=obj.fiscal_year,
            bps=obj.bps,
            eps=obj.eps,
            roe=obj.roe,
            net_assets=obj.net_assets,
            total_shares=obj.total_shares,
            revenue=obj.revenue,
            operating_income=obj.operating_income,
            eps_forecast=obj.eps_forecast,
            operating_cash_flow=obj.operating_cash_flow,
            free_cash_flow=obj.free_cash_flow,
            period_end_date=obj.period_end_date,
        )

    def _lookup_adj_factor(self, stock_id: int, period_end_date: date | None) -> Decimal:
        """決算期末日以降に発生した株式分割の累積調整係数を計算する。

        J-Quants の AdjFactor は分割発生日に記録される（例: 5:1分割 → AdjFactor=0.2）。
        期末日後から現在までに発生した分割イベントの AdjFactor を全て乗じて返す。

        例: period_end_date=2025-07-31, split AdjFactor=0.2 on 2026-01-19
            → cumulative = 0.2
            → effective_bps = bps × 0.2 = split-adjusted BPS

        AdjFactor が存在しない場合（データなし or 全て1.0）は 1.0 を返す。
        """
        from_date = period_end_date if period_end_date else date.today()
        # 期末日の翌日以降で AdjFactor != 1 のレコードを全件取得
        factors = list(
            StockPrice.objects.filter(
                stock_id=stock_id,
                date__gt=from_date,
            )
            .exclude(adj_factor=1)
            .values_list("adj_factor", flat=True)
        )
        if not factors:
            return Decimal("1")
        cumulative = Decimal("1")
        for f in factors:
            f_decimal = Decimal(str(f))
            if f_decimal > 0:
                cumulative *= f_decimal
        return cumulative

    def find_by_stock_id(self, stock_id: int) -> list[FinancialEntity]:
        entities = [self._to_entity(obj) for obj in StockFinancial.objects.filter(stock_id=stock_id)]
        for entity in entities:
            entity.adj_factor = self._lookup_adj_factor(stock_id, entity.period_end_date)
        return entities

    def _manual_to_entity(self, obj: FinancialManualInput) -> FinancialEntity:
        return FinancialEntity(
            id=None,  # 手動入力は t_stock_financials の id ではない
            stock_id=obj.stock_id,
            fiscal_year=obj.fiscal_year,
            bps=obj.bps or Decimal("0"),
            eps=obj.eps,
            roe=obj.roe,
            net_assets=None,
            total_shares=None,
            revenue=obj.revenue,
            operating_income=obj.operating_income,
            eps_forecast=obj.eps_forecast,
            is_manual=True,
        )

    def find_latest_by_stock_id(self, stock_id: int) -> FinancialEntity | None:
        # 両方取得して年度が新しい方を返す
        auto = StockFinancial.objects.filter(stock_id=stock_id).order_by("-fiscal_year").first()
        manual = FinancialManualInput.objects.filter(stock_id=stock_id).order_by("-fiscal_year").first()

        if auto and manual:
            # 手動入力の年度が新しければ手動データを優先（再上場銘柄の旧BPS問題への対処）
            if manual.fiscal_year > auto.fiscal_year:
                return self._manual_to_entity(manual)
            entity = self._to_entity(auto)
        elif auto:
            entity = self._to_entity(auto)
        elif manual:
            return self._manual_to_entity(manual)
        else:
            return None

        # 株式分割調整係数を付与（手動入力データには適用しない）
        entity.adj_factor = self._lookup_adj_factor(stock_id, entity.period_end_date)
        return entity

    def find_recent_by_stock_id(self, stock_id: int, limit: int = 4) -> list[FinancialEntity]:
        """最新N件の財務データを年度降順で返す（成長率計算用）。"""
        objs = StockFinancial.objects.filter(stock_id=stock_id).order_by("-fiscal_year")[:limit]
        return [self._to_entity(obj) for obj in objs]

    def save(self, entity: FinancialEntity) -> FinancialEntity:
        obj, _ = StockFinancial.objects.update_or_create(
            stock_id=entity.stock_id,
            fiscal_year=entity.fiscal_year,
            defaults={
                "bps": entity.bps,
                "eps": entity.eps,
                "roe": entity.roe,
                "net_assets": entity.net_assets,
                "total_shares": entity.total_shares,
                "revenue": entity.revenue,
                "operating_income": entity.operating_income,
                "eps_forecast": entity.eps_forecast,
                "period_end_date": entity.period_end_date,
                "operating_cash_flow": entity.operating_cash_flow,
                "free_cash_flow": entity.free_cash_flow,
            },
        )
        entity.id = obj.pk
        return entity

    def bulk_save(self, entities: list[FinancialEntity]) -> list[FinancialEntity]:
        for entity in entities:
            self.save(entity)
        return entities

    def find_all_latest(self) -> dict[int, FinancialEntity]:
        """全銘柄の最新財務データを一括取得（サブクエリで1回で取得）。"""
        from collections import defaultdict

        from django.db.models import OuterRef, Subquery

        # サブクエリ: 各stock_idの最大fiscal_yearを持つレコードのみ取得
        max_year_subq = (
            StockFinancial.objects.filter(stock_id=OuterRef("stock_id"))
            .order_by("-fiscal_year")
            .values("fiscal_year")[:1]
        )
        latest_objs = StockFinancial.objects.filter(fiscal_year=Subquery(max_year_subq))

        result: dict[int, FinancialEntity] = {}
        for obj in latest_objs:
            result[obj.stock_id] = self._to_entity(obj)

        # 手動入力データもマージ（年度が新しい場合は上書き）
        for manual_obj in FinancialManualInput.objects.all():
            existing = result.get(manual_obj.stock_id)
            if existing is None or manual_obj.fiscal_year > existing.fiscal_year:
                result[manual_obj.stock_id] = self._manual_to_entity(manual_obj)

        # adj_factor を一括計算（分割イベントがある銘柄のみ）
        split_factors: dict[int, list[tuple[date, Decimal]]] = defaultdict(list)
        for sp in StockPrice.objects.exclude(adj_factor=1).values_list("stock_id", "date", "adj_factor"):
            split_factors[sp[0]].append((sp[1], Decimal(str(sp[2]))))

        for sid, entity in result.items():
            if entity.is_manual:
                continue
            events = split_factors.get(sid)
            if not events or entity.period_end_date is None:
                entity.adj_factor = Decimal("1")
                continue
            cumulative = Decimal("1")
            for ev_date, factor in events:
                if ev_date > entity.period_end_date and factor > 0:
                    cumulative *= factor
            entity.adj_factor = cumulative

        return result

    def find_all_recent(self, limit: int = 4) -> dict[int, list[FinancialEntity]]:
        """全銘柄の直近N件の財務データを一括取得。"""
        from collections import defaultdict

        raw: dict[int, list[StockFinancial]] = defaultdict(list)
        for obj in StockFinancial.objects.order_by("stock_id", "-fiscal_year"):
            if len(raw[obj.stock_id]) < limit:
                raw[obj.stock_id].append(obj)

        return {sid: [self._to_entity(o) for o in objs] for sid, objs in raw.items()}

    def find_by_stock_ids(self, stock_ids: Sequence[int]) -> dict[int, list[FinancialEntity]]:
        """指定銘柄の全財務データを一括取得。{stock_id: [entities]} (fiscal_year DESC)"""
        from collections import defaultdict

        if not stock_ids:
            return {}
        raw: dict[int, list[StockFinancial]] = defaultdict(list)
        for obj in StockFinancial.objects.filter(stock_id__in=stock_ids).order_by("stock_id", "-fiscal_year"):
            raw[obj.stock_id].append(obj)
        return {sid: [self._to_entity(o) for o in objs] for sid, objs in raw.items()}


class DjangoPriceRepository(PriceRepository):
    """Django ORM による株価リポジトリ実装"""

    def _to_entity(self, obj: StockPrice) -> PriceEntity:
        return PriceEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            date=str(obj.date),
            close_price=obj.close_price,
            adj_factor=obj.adj_factor if obj.adj_factor is not None else Decimal("1"),
            pbr=obj.pbr,
            volume=obj.volume,
            is_limit_up=obj.is_limit_up,
            is_limit_down=obj.is_limit_down,
        )

    def find_by_stock_id(self, stock_id: int, limit: int = 100) -> list[PriceEntity]:
        return [self._to_entity(obj) for obj in StockPrice.objects.filter(stock_id=stock_id)[:limit]]

    def find_latest_by_stock_id(self, stock_id: int) -> PriceEntity | None:
        obj = StockPrice.objects.filter(stock_id=stock_id).first()
        return self._to_entity(obj) if obj else None

    def find_latest_date_by_stock_id(self, stock_id: int) -> str | None:
        obj = StockPrice.objects.filter(stock_id=stock_id).order_by("-date").values_list("date", flat=True).first()
        return str(obj) if obj else None

    def save(self, entity: PriceEntity) -> PriceEntity:
        obj, _ = StockPrice.objects.update_or_create(
            stock_id=entity.stock_id,
            date=entity.date,
            defaults={
                "close_price": entity.close_price,
                "adj_factor": entity.adj_factor,
                "pbr": entity.pbr,
                "volume": entity.volume,
                "is_limit_up": entity.is_limit_up,
                "is_limit_down": entity.is_limit_down,
            },
        )
        entity.id = obj.pk
        return entity

    def bulk_save(self, entities: list[PriceEntity]) -> list[PriceEntity]:
        for entity in entities:
            self.save(entity)
        return entities

    def find_price_near_date(self, stock_id: int, target_date: date) -> Decimal | None:
        """指定日に最も近い株価（前後7日以内）を返す。52週リターン計算用。"""
        from datetime import timedelta

        window_start = target_date - timedelta(days=7)
        window_end = target_date + timedelta(days=7)
        obj = (
            StockPrice.objects.filter(
                stock_id=stock_id,
                date__gte=window_start,
                date__lte=window_end,
            )
            .order_by("date")
            .values_list("close_price", flat=True)
            .first()
        )
        return obj

    def find_52w_high_low(self, stock_id: int) -> tuple[Decimal, Decimal] | None:
        """直近52週の最高値・最安値を返す。"""
        from datetime import timedelta

        from django.db.models import Max, Min

        cutoff = date.today() - timedelta(weeks=52)
        result = StockPrice.objects.filter(
            stock_id=stock_id,
            date__gte=cutoff,
        ).aggregate(high=Max("close_price"), low=Min("close_price"))
        if result["high"] is None or result["low"] is None:
            return None
        return (Decimal(str(result["high"])), Decimal(str(result["low"])))

    def find_all_52w_high_low(self) -> dict[int, tuple[Decimal, Decimal]]:
        """全銘柄の直近52週の最高値・最安値を一括取得。"""
        from datetime import timedelta

        from django.db.models import Max, Min

        cutoff = date.today() - timedelta(weeks=52)
        rows = (
            StockPrice.objects.filter(date__gte=cutoff)
            .values("stock_id")
            .annotate(high=Max("close_price"), low=Min("close_price"))
        )
        return {
            row["stock_id"]: (Decimal(str(row["high"])), Decimal(str(row["low"])))
            for row in rows
            if row["high"] is not None and row["low"] is not None
        }

    def find_all_recent_prices(self, limit: int = 25) -> dict[int, list[PriceEntity]]:
        """全銘柄の直近N日の株価を一括取得（日付降順）。

        values() で軽量化し、ORM オブジェクト生成コストを削減。
        cutoff は「DB 上の最新日」起点で limit*2 日遡る（同期が止まっていても直近 N 件取れる）。
        """
        from datetime import timedelta

        from django.db.models import Max

        anchor = StockPrice.objects.aggregate(d=Max("date"))["d"] or date.today()
        cutoff = anchor - timedelta(days=limit * 2)
        rows = (
            StockPrice.objects.filter(date__gte=cutoff)
            .order_by("stock_id", "-date")
            .values("stock_id", "date", "close_price", "adj_factor", "volume", "is_limit_up", "is_limit_down")
        )

        result: dict[int, list[PriceEntity]] = {}
        for row in rows:
            sid = row["stock_id"]
            if sid not in result:
                result[sid] = []
            if len(result[sid]) < limit:
                result[sid].append(
                    PriceEntity(
                        stock_id=sid,
                        date=str(row["date"]),
                        close_price=row["close_price"],
                        adj_factor=row["adj_factor"],
                        volume=row["volume"],
                        is_limit_up=row.get("is_limit_up", False),
                        is_limit_down=row.get("is_limit_down", False),
                    )
                )
        return result


class DjangoDividendRepository(DividendRepository):
    """Django ORM による配当・分配金リポジトリ実装"""

    def _to_entity(self, obj: Dividend) -> DividendEntity:
        return DividendEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            ex_dividend_date=obj.ex_dividend_date,
            dividends_per_share=obj.dividends_per_share,
            record_date=obj.record_date,
            payable_date=obj.payable_date,
            source=obj.source,
        )

    def bulk_save(self, entities: list[DividendEntity]) -> None:
        for entity in entities:
            Dividend.objects.update_or_create(
                stock_id=entity.stock_id,
                ex_dividend_date=entity.ex_dividend_date,
                defaults={
                    "dividends_per_share": entity.dividends_per_share,
                    "record_date": entity.record_date,
                    "payable_date": entity.payable_date,
                    "source": entity.source,
                },
            )

    def find_by_stock_id(self, stock_id: int, limit: int = 20) -> list[DividendEntity]:
        return [self._to_entity(obj) for obj in Dividend.objects.filter(stock_id=stock_id)[:limit]]

    def find_annual_total(self, stock_id: int) -> Decimal | None:
        """直近12ヶ月の配当/分配金合計を返す。"""
        from datetime import timedelta

        from django.db.models import Sum

        cutoff = date.today() - timedelta(days=365)
        result: Decimal | None = Dividend.objects.filter(
            stock_id=stock_id,
            ex_dividend_date__gte=cutoff,
        ).aggregate(total=Sum("dividends_per_share"))["total"]
        return result

    def find_all_annual_totals(self, stock_ids: list[int]) -> dict[int, Decimal]:
        """複数銘柄の直近12ヶ月配当合計を一括取得。"""
        from datetime import timedelta

        from django.db.models import Sum

        cutoff = date.today() - timedelta(days=365)
        qs = (
            Dividend.objects.filter(
                stock_id__in=stock_ids,
                ex_dividend_date__gte=cutoff,
            )
            .values("stock_id")
            .annotate(total=Sum("dividends_per_share"))
        )
        return {row["stock_id"]: row["total"] for row in qs if row["total"]}

    def find_all_by_stock_ids(self, stock_ids: list[int]) -> dict[int, list[DividendEntity]]:
        """複数銘柄の全配当履歴を一括取得。"""
        result: dict[int, list[DividendEntity]] = {}
        qs = Dividend.objects.filter(stock_id__in=stock_ids).order_by("stock_id", "-ex_dividend_date")
        for obj in qs:
            entity = self._to_entity(obj)
            result.setdefault(obj.stock_id, []).append(entity)
        return result

    def find_upcoming_by_stock_ids(
        self,
        stock_ids: list[int],
        *,
        from_date: date,
        to_date: date,
    ) -> list[DividendEntity]:
        """指定銘柄群の今後の配当予定（ex_dividend_date が範囲内）を昇順で返す。"""
        if not stock_ids:
            return []
        qs = Dividend.objects.filter(
            stock_id__in=stock_ids,
            ex_dividend_date__gte=from_date,
            ex_dividend_date__lte=to_date,
        ).order_by("ex_dividend_date", "stock_id")
        return [self._to_entity(obj) for obj in qs]


class DjangoApiConfigRepository(ApiConfigRepository):
    """Django ORM によるAPI設定リポジトリ実装"""

    def _to_entity(self, obj: ApiConfig) -> ApiConfigEntity:
        return ApiConfigEntity(
            id=obj.pk,
            provider=obj.provider,
            is_enabled=obj.is_enabled,
            api_key=obj.api_key,
            plan=obj.plan,
            config_json=obj.config_json,
        )

    def find_by_provider(self, provider: str) -> ApiConfigEntity | None:
        try:
            return self._to_entity(ApiConfig.objects.get(provider=provider))
        except ApiConfig.DoesNotExist:
            return None

    def save(self, entity: ApiConfigEntity) -> ApiConfigEntity:
        obj, _ = ApiConfig.objects.update_or_create(
            provider=entity.provider,
            defaults={
                "is_enabled": entity.is_enabled,
                "api_key": entity.api_key,
                "plan": entity.plan,
                "config_json": entity.config_json,
            },
        )
        entity.id = obj.pk
        return entity


class DjangoSyncLogRepository(SyncLogRepository):
    """Django ORM による同期ログリポジトリ実装"""

    def _to_entity(self, obj: SyncLog) -> SyncLogEntity:
        return SyncLogEntity(
            id=obj.pk,
            sync_type=obj.sync_type,
            provider=obj.provider,
            market=obj.market,
            status=obj.status,
            started_at=obj.started_at,
            finished_at=obj.finished_at,
            total_count=obj.total_count,
            success_count=obj.success_count,
            error_count=obj.error_count,
            error_details=obj.error_details,
        )

    def save(self, entity: SyncLogEntity) -> SyncLogEntity:
        if entity.id:
            SyncLog.objects.filter(pk=entity.id).update(
                status=entity.status,
                finished_at=entity.finished_at,
                total_count=entity.total_count,
                success_count=entity.success_count,
                error_count=entity.error_count,
                error_details=entity.error_details,
            )
            return entity
        obj = SyncLog.objects.create(
            sync_type=entity.sync_type,
            provider=entity.provider,
            market=entity.market,
            status=entity.status,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            total_count=entity.total_count,
            success_count=entity.success_count,
            error_count=entity.error_count,
            error_details=entity.error_details,
        )
        entity.id = obj.pk
        return entity

    def find_latest_by_type(self, sync_type: str, market: str) -> SyncLogEntity | None:
        obj = SyncLog.objects.filter(sync_type=sync_type, market=market, status="success").first()
        return self._to_entity(obj) if obj else None

    def list_recent(self, limit: int = 20) -> list[SyncLogEntity]:
        # 一覧表示用途では error_details (JSON) は不要。
        # only() で除外しないと SELECT * + ORDER BY -started_at LIMIT N が
        # MySQL の sort_buffer_size を超えて 1038 'Out of sort memory' に
        # なる (本番で発生実績あり、t_sync_logs に started_at の index も
        # 追加済み)。SyncLogEntity の error_details は空配列で返す。
        qs = SyncLog.objects.only(
            "id",
            "sync_type",
            "provider",
            "market",
            "status",
            "started_at",
            "finished_at",
            "total_count",
            "success_count",
            "error_count",
        )[:limit]
        return [
            SyncLogEntity(
                id=obj.pk,
                sync_type=obj.sync_type,
                provider=obj.provider,
                market=obj.market,
                status=obj.status,
                started_at=obj.started_at,
                finished_at=obj.finished_at,
                total_count=obj.total_count,
                success_count=obj.success_count,
                error_count=obj.error_count,
                error_details=[],
            )
            for obj in qs
        ]


class DjangoMarginRepository(MarginRepository):
    """Django ORM による信用取引残高リポジトリ実装"""

    def _to_entity(self, obj: MarginBalance) -> MarginBalanceEntity:
        return MarginBalanceEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            date=obj.date,
            long_balance=obj.long_balance,
            long_balance_change=obj.long_balance_change,
            short_balance=obj.short_balance,
            short_balance_change=obj.short_balance_change,
            sl_ratio=obj.sl_ratio,
        )

    def find_latest_by_stock_id(self, stock_id: int) -> MarginBalanceEntity | None:
        obj = MarginBalance.objects.filter(stock_id=stock_id).first()
        return self._to_entity(obj) if obj else None

    def find_recent_by_stock_id(self, stock_id: int, limit: int = 8) -> list[MarginBalanceEntity]:
        objs = MarginBalance.objects.filter(stock_id=stock_id)[:limit]
        return [self._to_entity(obj) for obj in objs]

    def find_all_latest(self) -> dict[int, MarginBalanceEntity]:
        """全銘柄の最新信用残高を一括取得（サブクエリ）。"""
        from django.db.models import OuterRef, Subquery

        max_date_subq = MarginBalance.objects.filter(stock_id=OuterRef("stock_id")).order_by("-date").values("date")[:1]
        return {
            obj.stock_id: self._to_entity(obj) for obj in MarginBalance.objects.filter(date=Subquery(max_date_subq))
        }

    def bulk_save(self, data_list: list[MarketMarginData], stock_map: dict[str, int]) -> int:
        saved = 0
        for data in data_list:
            stock_id = stock_map.get(data.code)
            if stock_id is None:
                continue
            _, created = MarginBalance.objects.update_or_create(
                stock_id=stock_id,
                date=data.date,
                defaults={
                    "long_balance": data.long_balance,
                    "long_balance_change": data.long_balance_change,
                    "short_balance": data.short_balance,
                    "short_balance_change": data.short_balance_change,
                    "sl_ratio": data.sl_ratio,
                },
            )
            saved += 1
        return saved


class DjangoOwnerShareholderRepository(OwnerShareholderRepository):
    """Django ORM によるオーナー大株主リポジトリ実装"""

    def _to_entity(self, obj: OwnerShareholder) -> OwnerShareholderEntity:
        return OwnerShareholderEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            representative_name=obj.representative_name,
            shareholder_name=obj.shareholder_name,
            shareholder_rank=obj.shareholder_rank,
            ownership_ratio=obj.ownership_ratio,
            match_type=obj.match_type,
            fiscal_year=obj.fiscal_year,
            doc_id=obj.doc_id,
        )

    def find_by_stock_id(self, stock_id: int) -> list[OwnerShareholderEntity]:
        return [self._to_entity(obj) for obj in OwnerShareholder.objects.filter(stock_id=stock_id)]

    def find_latest_by_stock_ids(self, stock_ids: list[int]) -> dict[int, list[OwnerShareholderEntity]]:
        """各銘柄の最新年度データのみ取得。"""
        from django.db.models import Max

        # 各銘柄の最新fiscal_yearを取得
        latest_years = dict(
            OwnerShareholder.objects.filter(stock_id__in=stock_ids)
            .values_list("stock_id")
            .annotate(max_fy=Max("fiscal_year"))
            .values_list("stock_id", "max_fy")
        )
        if not latest_years:
            return {}

        # 最新年度のデータのみ取得
        from django.db.models import Q

        q = Q()
        for sid, fy in latest_years.items():
            q |= Q(stock_id=sid, fiscal_year=fy)

        result: dict[int, list[OwnerShareholderEntity]] = {}
        for obj in OwnerShareholder.objects.filter(q):
            entity = self._to_entity(obj)
            result.setdefault(obj.stock_id, []).append(entity)
        return result

    def save_batch(self, stock_id: int, fiscal_year: int, entities: list[OwnerShareholderEntity]) -> None:
        """指定銘柄・年度のデータを全削除してから挿入。"""
        OwnerShareholder.objects.filter(stock_id=stock_id, fiscal_year=fiscal_year).delete()
        for entity in entities:
            OwnerShareholder.objects.create(
                stock_id=entity.stock_id,
                representative_name=entity.representative_name,
                shareholder_name=entity.shareholder_name,
                shareholder_rank=entity.shareholder_rank,
                ownership_ratio=entity.ownership_ratio,
                match_type=entity.match_type,
                fiscal_year=entity.fiscal_year,
                doc_id=entity.doc_id,
            )


class DjangoShareholderRawRepository(ShareholderRawRepository):
    """Django ORM による大株主生データリポジトリ実装"""

    def save_batch(self, stock_id: int, fiscal_year: int, entities: list[ShareholderRawEntity]) -> None:
        ShareholderRaw.objects.filter(stock_id=stock_id, fiscal_year=fiscal_year).delete()
        for entity in entities:
            ShareholderRaw.objects.create(
                stock_id=entity.stock_id,
                shareholder_name=entity.shareholder_name,
                shareholder_rank=entity.shareholder_rank,
                ownership_ratio=entity.ownership_ratio,
                shares_held=entity.shares_held,
                fiscal_year=entity.fiscal_year,
                doc_id=entity.doc_id,
            )

    def find_by_stock_id(self, stock_id: int) -> list[ShareholderRawEntity]:
        return [
            ShareholderRawEntity(
                id=obj.pk,
                stock_id=obj.stock_id,
                shareholder_name=obj.shareholder_name,
                shareholder_rank=obj.shareholder_rank,
                ownership_ratio=obj.ownership_ratio,
                shares_held=obj.shares_held,
                fiscal_year=obj.fiscal_year,
                doc_id=obj.doc_id,
            )
            for obj in ShareholderRaw.objects.filter(stock_id=stock_id)
        ]


class DjangoScreeningPresetRepository(ScreeningPresetRepository):
    """Django ORM によるスクリーニングプリセットリポジトリ実装"""

    def _to_entity(self, obj: ScreeningPreset) -> ScreeningPresetEntity:
        return ScreeningPresetEntity(
            id=obj.pk,
            user_id=obj.user_id,
            name=obj.name,
            priority=obj.priority,
            filters=obj.filters,
        )

    def find_by_user_id(self, user_id: int) -> list[ScreeningPresetEntity]:
        return [self._to_entity(obj) for obj in ScreeningPreset.objects.filter(user_id=user_id)]

    def find_by_id(self, preset_id: int, user_id: int) -> ScreeningPresetEntity | None:
        try:
            obj = ScreeningPreset.objects.get(pk=preset_id, user_id=user_id)
        except ScreeningPreset.DoesNotExist:
            return None
        return self._to_entity(obj)

    def save(self, entity: ScreeningPresetEntity) -> ScreeningPresetEntity:
        if entity.id:
            ScreeningPreset.objects.filter(pk=entity.id, user_id=entity.user_id).update(
                name=entity.name,
                priority=entity.priority,
                filters=entity.filters,
            )
            obj = ScreeningPreset.objects.get(pk=entity.id)
        else:
            obj = ScreeningPreset.objects.create(
                user_id=entity.user_id,
                name=entity.name,
                priority=entity.priority,
                filters=entity.filters,
            )
        return self._to_entity(obj)

    def delete(self, preset_id: int, user_id: int) -> bool:
        deleted, _ = ScreeningPreset.objects.filter(pk=preset_id, user_id=user_id).delete()
        return deleted > 0


class DjangoDailyMoversRepository(DailyMoversRepository):
    """日次急騰急落集計の Django ORM 実装。"""

    @staticmethod
    def _to_entity(obj: DailyMovers) -> DailyMoversEntity:
        return DailyMoversEntity(
            id=obj.pk,
            stock_id=obj.stock_id,
            date=obj.date,
            close_price=obj.close_price,
            prev_close=obj.prev_close,
            change_pct=obj.change_pct,
            volume=obj.volume,
            volume_ratio_20d=obj.volume_ratio_20d,
            is_limit_up=obj.is_limit_up,
            is_limit_down=obj.is_limit_down,
        )

    def find_latest_date(self) -> date | None:
        obj = DailyMovers.objects.order_by("-date").values_list("date", flat=True).first()
        return obj

    def find_by_date(self, target_date: date) -> list[DailyMoversEntity]:
        return [self._to_entity(obj) for obj in DailyMovers.objects.filter(date=target_date).select_related("stock")]

    def find_by_date_and_stock_ids(
        self,
        target_date: date,
        stock_ids: list[int],
    ) -> list[DailyMoversEntity]:
        if not stock_ids:
            return []
        return [
            self._to_entity(obj)
            for obj in DailyMovers.objects.filter(date=target_date, stock_id__in=stock_ids).select_related("stock")
        ]

    def bulk_replace(self, target_date: date, entities: list[DailyMoversEntity]) -> int:
        from django.db import transaction

        with transaction.atomic():
            DailyMovers.objects.filter(date=target_date).delete()
            objs = [
                DailyMovers(
                    stock_id=e.stock_id,
                    date=e.date,
                    close_price=e.close_price,
                    prev_close=e.prev_close,
                    change_pct=e.change_pct,
                    volume=e.volume,
                    volume_ratio_20d=e.volume_ratio_20d,
                    is_limit_up=e.is_limit_up,
                    is_limit_down=e.is_limit_down,
                )
                for e in entities
            ]
            created = DailyMovers.objects.bulk_create(objs)
            return len(created)
