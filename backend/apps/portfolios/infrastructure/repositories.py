from apps.portfolios.domain.entities import (
    AccountHoldingEntity,
    AccountSnapshotEntity,
    FamilyMemberEntity,
    PortfolioAccountEntity,
    WatchlistItemEntity,
)
from apps.portfolios.domain.repositories import (
    AccountSnapshotRepository,
    FamilyMemberRepository,
    PortfolioAccountRepository,
    WatchlistRepository,
)
from apps.portfolios.models import (
    AccountHolding,
    AccountSnapshot,
    FamilyMember,
    PortfolioAccount,
    WatchlistItem,
)
from apps.stocks.models import Stock

# ============================================================
# 家族ポートフォリオ（新実装）
# ============================================================


class DjangoFamilyMemberRepository(FamilyMemberRepository):
    def find_by_user(self, user_id: int) -> list[FamilyMemberEntity]:
        return [self._to_entity(m) for m in FamilyMember.objects.filter(user_id=user_id)]

    def find_by_id(self, member_id: int, user_id: int) -> FamilyMemberEntity | None:
        try:
            return self._to_entity(FamilyMember.objects.get(pk=member_id, user_id=user_id))
        except FamilyMember.DoesNotExist:
            return None

    def save(self, entity: FamilyMemberEntity) -> FamilyMemberEntity:
        if entity.id:
            FamilyMember.objects.filter(pk=entity.id, user_id=entity.user_id).update(
                name=entity.name,
                role=entity.role,
                color_code=entity.color_code,
                display_order=entity.display_order,
                include_in_family_total=entity.include_in_family_total,
            )
            obj = FamilyMember.objects.get(pk=entity.id)
        else:
            obj = FamilyMember.objects.create(
                user_id=entity.user_id,
                name=entity.name,
                role=entity.role,
                color_code=entity.color_code,
                display_order=entity.display_order,
                include_in_family_total=entity.include_in_family_total,
            )
        entity.id = obj.pk
        return entity

    def delete(self, member_id: int, user_id: int) -> None:
        FamilyMember.objects.filter(pk=member_id, user_id=user_id).delete()

    def _to_entity(self, obj: FamilyMember) -> FamilyMemberEntity:
        return FamilyMemberEntity(
            id=obj.pk,
            user_id=obj.user_id,
            name=obj.name,
            role=obj.role,
            color_code=obj.color_code,
            display_order=obj.display_order,
            include_in_family_total=obj.include_in_family_total,
        )


class DjangoPortfolioAccountRepository(PortfolioAccountRepository):
    def find_by_user(self, user_id: int) -> list[PortfolioAccountEntity]:
        qs = PortfolioAccount.objects.filter(family_member__user_id=user_id).select_related("family_member")
        return [self._to_entity(a) for a in qs]

    def find_by_id(self, account_id: int, user_id: int) -> PortfolioAccountEntity | None:
        try:
            obj = PortfolioAccount.objects.select_related("family_member").get(
                pk=account_id, family_member__user_id=user_id
            )
            return self._to_entity(obj)
        except PortfolioAccount.DoesNotExist:
            return None

    def save(self, entity: PortfolioAccountEntity) -> PortfolioAccountEntity:
        defaults = {
            "institution": entity.institution,
            "institution_type": entity.institution_type,
            "asset_class": entity.asset_class,
            "trading_type": entity.trading_type,
            "nickname": entity.nickname,
            "currency": entity.currency,
            "notes": entity.notes,
            "is_active": entity.is_active,
            "expected_return_rate": entity.expected_return_rate,
            "margin_credit_type": entity.margin_credit_type,
            "margin_interest_rate": entity.margin_interest_rate,
        }
        if entity.id:
            PortfolioAccount.objects.filter(pk=entity.id).update(**defaults)
            obj = PortfolioAccount.objects.get(pk=entity.id)
        else:
            obj = PortfolioAccount.objects.create(family_member_id=entity.family_member_id, **defaults)
        entity.id = obj.pk
        return entity

    def delete(self, account_id: int, user_id: int) -> None:
        PortfolioAccount.objects.filter(pk=account_id, family_member__user_id=user_id).delete()

    def _to_entity(self, obj: PortfolioAccount) -> PortfolioAccountEntity:
        return PortfolioAccountEntity(
            id=obj.pk,
            family_member_id=obj.family_member_id,
            institution=obj.institution,
            institution_type=obj.institution_type,
            asset_class=obj.asset_class,
            trading_type=obj.trading_type,
            nickname=obj.nickname,
            currency=obj.currency,
            notes=obj.notes,
            is_active=obj.is_active,
            expected_return_rate=obj.expected_return_rate,
            family_member_name=obj.family_member.name,
            margin_credit_type=obj.margin_credit_type,
            margin_interest_rate=obj.margin_interest_rate,
        )


class DjangoAccountSnapshotRepository(AccountSnapshotRepository):
    def find_by_account(self, account_id: int, user_id: int) -> list[AccountSnapshotEntity]:
        qs = (
            AccountSnapshot.objects.filter(
                account_id=account_id,
                account__family_member__user_id=user_id,
            )
            .prefetch_related("holdings")
            .order_by("-snapshot_date")
        )
        return [self._to_entity(s) for s in qs]

    def find_by_account_paginated(
        self, account_id: int, user_id: int, limit: int, offset: int
    ) -> tuple[list[AccountSnapshotEntity], int]:
        base = AccountSnapshot.objects.filter(
            account_id=account_id,
            account__family_member__user_id=user_id,
        )
        total = base.count()
        qs = base.order_by("-snapshot_date")[offset : offset + limit]
        results = [
            AccountSnapshotEntity(
                id=obj.pk,
                account_id=obj.account_id,
                snapshot_date=str(obj.snapshot_date),
                total_value_jpy=obj.total_value_jpy,
                total_cost_jpy=obj.total_cost_jpy,
                exchange_rate=obj.exchange_rate,
                notes=obj.notes,
                holdings=[],
            )
            for obj in qs
        ]
        return results, total

    def find_by_account_and_date(
        self, account_id: int, snapshot_date: str, user_id: int
    ) -> AccountSnapshotEntity | None:
        try:
            obj = AccountSnapshot.objects.prefetch_related("holdings").get(
                account_id=account_id,
                snapshot_date=snapshot_date,
                account__family_member__user_id=user_id,
            )
            return self._to_entity(obj)
        except AccountSnapshot.DoesNotExist:
            return None

    def save(self, entity: AccountSnapshotEntity, user_id: int) -> AccountSnapshotEntity:
        # ownership check
        account = PortfolioAccount.objects.get(pk=entity.account_id, family_member__user_id=user_id)
        obj, _ = AccountSnapshot.objects.update_or_create(
            account=account,
            snapshot_date=entity.snapshot_date,
            defaults={
                "total_value_jpy": entity.total_value_jpy,
                "total_cost_jpy": entity.total_cost_jpy,
                "exchange_rate": entity.exchange_rate,
                "notes": entity.notes,
            },
        )
        # 保有明細を再作成
        obj.holdings.all().delete()

        # stock_id 自動リンク: ticker_code → m_stocks.code
        ticker_codes_to_resolve = {h.ticker_code for h in entity.holdings if h.stock_id is None and h.ticker_code}
        stock_id_map: dict[str, int] = {}
        if ticker_codes_to_resolve:
            for s in Stock.objects.filter(code__in=ticker_codes_to_resolve).only("id", "code"):
                stock_id_map[s.code] = s.pk

        # proxy_stock_id 自動リンク: 投信(asset_type="fund" かつ ticker_code なし)は
        # 銘柄名から proxy ETF を解決する。設定しないと MTD 日次変動計算で取りこぼされる。
        # entity 側に既に proxy_stock_id があればそれを優先。
        from apps.portfolios.application.services.fund_proxy_service import resolve_proxy_code

        proxy_codes_to_resolve = {
            code
            for h in entity.holdings
            if h.proxy_stock_id is None
            and h.asset_type == "fund"
            and not h.ticker_code
            and (code := resolve_proxy_code(h.asset_name)) is not None
        }
        proxy_code_map: dict[str, int] = {}
        if proxy_codes_to_resolve:
            for s in Stock.objects.filter(code__in=proxy_codes_to_resolve).only("id", "code"):
                proxy_code_map[s.code] = s.pk

        for h in entity.holdings:
            resolved_stock_id = h.stock_id or stock_id_map.get(h.ticker_code or "")
            resolved_proxy_id = h.proxy_stock_id
            if resolved_proxy_id is None and h.asset_type == "fund" and not h.ticker_code:
                proxy_code = resolve_proxy_code(h.asset_name)
                resolved_proxy_id = proxy_code_map.get(proxy_code) if proxy_code else None
            AccountHolding.objects.create(
                snapshot=obj,
                stock_id=resolved_stock_id,
                proxy_stock_id=resolved_proxy_id,
                ticker_code=h.ticker_code,
                asset_name=h.asset_name,
                asset_type=h.asset_type,
                quantity=h.quantity,
                unit_price=h.unit_price,
                value_jpy=h.value_jpy,
                cost_jpy=h.cost_jpy,
                built_date=h.built_date,
            )
        entity.id = obj.pk
        return entity

    def delete(self, account_id: int, snapshot_date: str, user_id: int) -> None:
        AccountSnapshot.objects.filter(
            account_id=account_id,
            snapshot_date=snapshot_date,
            account__family_member__user_id=user_id,
        ).delete()

    def find_latest_single(self, account_id: int, user_id: int) -> AccountSnapshotEntity | None:
        """指定口座の最新スナップショットを1件返す"""
        obj = (
            AccountSnapshot.objects.filter(
                account_id=account_id,
                account__family_member__user_id=user_id,
            )
            .prefetch_related("holdings")
            .order_by("-snapshot_date")
            .first()
        )
        return self._to_entity(obj) if obj else None

    def find_all_by_user(self, user_id: int) -> list[AccountSnapshotEntity]:
        """全口座の全スナップショットを返す（holdings は不要なので取得しない）"""
        qs = (
            AccountSnapshot.objects.filter(
                account__family_member__user_id=user_id,
            )
            .select_related("account__family_member")
            .order_by("snapshot_date")
        )
        results: list[AccountSnapshotEntity] = []
        for obj in qs:
            results.append(
                AccountSnapshotEntity(
                    id=obj.pk,
                    account_id=obj.account_id,
                    snapshot_date=str(obj.snapshot_date),
                    total_value_jpy=obj.total_value_jpy,
                    total_cost_jpy=obj.total_cost_jpy,
                    exchange_rate=obj.exchange_rate,
                    notes=obj.notes,
                    holdings=[],
                )
            )
        return results

    def find_earliest_date_by_user(self, user_id: int) -> str | None:
        from django.db.models import Min

        result = AccountSnapshot.objects.filter(
            account__family_member__user_id=user_id,
        ).aggregate(earliest=Min("snapshot_date"))
        earliest = result.get("earliest")
        return str(earliest) if earliest is not None else None

    def find_latest_by_user(self, user_id: int) -> list[AccountSnapshotEntity]:
        """各口座の最新スナップショットを1件ずつ返す"""
        from django.db.models import OuterRef, Subquery

        latest_dates = (
            AccountSnapshot.objects.filter(
                account=OuterRef("account"),
                account__family_member__user_id=user_id,
            )
            .order_by("-snapshot_date")
            .values("snapshot_date")[:1]
        )
        qs = (
            AccountSnapshot.objects.filter(
                snapshot_date=Subquery(latest_dates),
                account__family_member__user_id=user_id,
            )
            .select_related("account__family_member")
            .prefetch_related("holdings")
        )
        return [self._to_entity(s) for s in qs]

    def find_each_account_latest_before(
        self, user_id: int, as_of_date: str, with_holdings: bool = False
    ) -> list[AccountSnapshotEntity]:
        """各口座について、as_of_date 以前で最新のスナップショットを 1 件ずつ返す。

        月初来損益 (MTD) の baseline 計算に使用。
        with_holdings=False (デフォルト) は holdings を読み込まず軽量。
        with_holdings=True は DynamicValuationService で動的再評価する用途に holdings 込み。
        """
        from django.db.models import OuterRef, Subquery

        latest_dates = (
            AccountSnapshot.objects.filter(
                account=OuterRef("account"),
                account__family_member__user_id=user_id,
                snapshot_date__lte=as_of_date,
            )
            .order_by("-snapshot_date")
            .values("snapshot_date")[:1]
        )
        qs = AccountSnapshot.objects.filter(
            snapshot_date=Subquery(latest_dates),
            snapshot_date__lte=as_of_date,
            account__family_member__user_id=user_id,
        ).select_related("account")
        if with_holdings:
            qs = qs.prefetch_related("holdings")
            return [self._to_entity(obj) for obj in qs]
        return [
            AccountSnapshotEntity(
                id=obj.pk,
                account_id=obj.account_id,
                snapshot_date=str(obj.snapshot_date),
                total_value_jpy=obj.total_value_jpy,
                total_cost_jpy=obj.total_cost_jpy,
                exchange_rate=obj.exchange_rate,
                notes=obj.notes,
                holdings=[],
            )
            for obj in qs
        ]

    def _to_entity(self, obj: AccountSnapshot) -> AccountSnapshotEntity:
        holdings = [
            AccountHoldingEntity(
                id=h.pk,
                snapshot_id=obj.pk,
                ticker_code=h.ticker_code,
                asset_name=h.asset_name,
                asset_type=h.asset_type,
                quantity=h.quantity,
                unit_price=h.unit_price,
                value_jpy=h.value_jpy,
                cost_jpy=h.cost_jpy,
                stock_id=h.stock_id,
                proxy_stock_id=h.proxy_stock_id,
                built_date=h.built_date,
            )
            for h in obj.holdings.all()
        ]
        return AccountSnapshotEntity(
            id=obj.pk,
            account_id=obj.account_id,
            snapshot_date=str(obj.snapshot_date),
            total_value_jpy=obj.total_value_jpy,
            total_cost_jpy=obj.total_cost_jpy,
            exchange_rate=obj.exchange_rate,
            notes=obj.notes,
            holdings=holdings,
        )


# ============================================================
# 既存実装
# ============================================================


class DjangoWatchlistRepository(WatchlistRepository):
    def find_by_user(self, user_id: int) -> list[WatchlistItemEntity]:
        items = WatchlistItem.objects.filter(user_id=user_id).select_related("stock")
        return [self._to_entity(item) for item in items]

    def find_by_user_and_stock(self, user_id: int, stock_code: str) -> WatchlistItemEntity | None:
        try:
            item = WatchlistItem.objects.select_related("stock").get(user_id=user_id, stock__code=stock_code)
            return self._to_entity(item)
        except WatchlistItem.DoesNotExist:
            return None

    def add(self, entity: WatchlistItemEntity) -> WatchlistItemEntity:
        stock = Stock.objects.get(code=entity.stock_code)
        item, _ = WatchlistItem.objects.get_or_create(
            user_id=entity.user_id,
            stock=stock,
            defaults={"memo": entity.memo},
        )
        return self._to_entity(item)

    def remove(self, user_id: int, stock_code: str) -> None:
        WatchlistItem.objects.filter(user_id=user_id, stock__code=stock_code).delete()

    def _to_entity(self, item: WatchlistItem) -> WatchlistItemEntity:
        return WatchlistItemEntity(
            id=item.pk,
            user_id=item.user_id,
            stock_id=item.stock_id,
            stock_code=item.stock.code,
            stock_name=item.stock.name,
            memo=item.memo,
        )
