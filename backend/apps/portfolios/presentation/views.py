import datetime
import logging
from decimal import Decimal
from typing import Any, cast

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.portfolios.application.services.csv_import_service import (
    extract_date_from_filename,
    get_csv_parser,
)
from apps.portfolios.domain.entities import (
    AccountHoldingEntity,
    AccountSnapshotEntity,
    FamilyMemberEntity,
    PortfolioAccountEntity,
    WatchlistItemEntity,
)
from apps.portfolios.infrastructure.repositories import (
    DjangoAccountSnapshotRepository,
    DjangoFamilyMemberRepository,
    DjangoPortfolioAccountRepository,
    DjangoWatchlistRepository,
)

from .serializers import (
    AccountSnapshotSerializer,
    FamilyMemberSerializer,
    PortfolioAccountSerializer,
    WatchlistItemSerializer,
)

logger = logging.getLogger(__name__)

# ============================================================
# 家族ポートフォリオAPI（新ビュー）
# ============================================================


def _effective_account_value(
    val: Decimal | int | None,
    cost: Decimal | int | None,
    is_margin: bool,
) -> Decimal:
    """口座の評価額を「資産計上ベース」で返す。

    - 現物口座: 時価 (val) をそのまま返す
    - 信用口座: 評価損益 (val - cost) のみを返す。借入金で建てているため
      時価そのものを資産にカウントすると過大評価になる。
    - val が欠損 → 0
    - 信用かつ cost 欠損 → 0
    """
    if val is None:
        return Decimal(0)
    if is_margin:
        if cost is None:
            return Decimal(0)
        return Decimal(val) - Decimal(cost)
    return Decimal(val)


def _member_to_dict(e: FamilyMemberEntity) -> dict[str, Any]:
    return {
        "id": e.id,
        "name": e.name,
        "role": e.role,
        "color_code": e.color_code,
        "display_order": e.display_order,
        "include_in_family_total": e.include_in_family_total,
    }


def _account_to_dict(e: PortfolioAccountEntity) -> dict[str, Any]:
    from apps.portfolios.models import PortfolioAccount

    it_labels = dict(PortfolioAccount.InstitutionType.choices)
    ac_labels = dict(PortfolioAccount.AssetClass.choices)
    tt_labels = dict(PortfolioAccount.TradingType.choices)
    mct_labels = dict(PortfolioAccount.MarginCreditType.choices)
    return {
        "id": e.id,
        "family_member_id": e.family_member_id,
        "family_member_name": e.family_member_name,
        "institution": e.institution,
        "institution_type": e.institution_type,
        "institution_type_display": it_labels.get(e.institution_type, e.institution_type),
        "asset_class": e.asset_class,
        "asset_class_display": ac_labels.get(e.asset_class, e.asset_class),
        "trading_type": e.trading_type,
        "trading_type_display": tt_labels.get(e.trading_type, e.trading_type),
        "nickname": e.nickname,
        "currency": e.currency,
        "notes": e.notes,
        "is_active": e.is_active,
        "expected_return_rate": str(e.expected_return_rate) if e.expected_return_rate is not None else None,
        "margin_credit_type": e.margin_credit_type,
        "margin_credit_type_display": (mct_labels.get(e.margin_credit_type, "") if e.margin_credit_type else ""),
        "margin_interest_rate": (str(e.margin_interest_rate) if e.margin_interest_rate is not None else None),
    }


def _snapshot_to_dict(e: AccountSnapshotEntity) -> dict[str, Any]:
    return {
        "id": e.id,
        "account_id": e.account_id,
        "snapshot_date": e.snapshot_date,
        "total_value_jpy": str(e.total_value_jpy),
        "total_cost_jpy": str(e.total_cost_jpy) if e.total_cost_jpy is not None else None,
        "exchange_rate": str(e.exchange_rate) if e.exchange_rate is not None else None,
        "notes": e.notes,
        "holdings": [
            {
                "id": h.id,
                "stock_id": h.stock_id,
                "ticker_code": h.ticker_code,
                "asset_name": h.asset_name,
                "asset_type": h.asset_type,
                "quantity": str(h.quantity) if h.quantity is not None else None,
                "unit_price": str(h.unit_price) if h.unit_price is not None else None,
                "value_jpy": str(h.value_jpy),
                "cost_jpy": str(h.cost_jpy) if h.cost_jpy is not None else None,
                "built_date": h.built_date.isoformat() if h.built_date is not None else None,
            }
            for h in e.holdings
        ],
    }


class FamilyMemberListView(APIView):
    """GET /api/family-members/  POST /api/family-members/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        repo = DjangoFamilyMemberRepository()
        members = repo.find_by_user(cast("int", request.user.pk))
        return Response([_member_to_dict(m) for m in members])

    def post(self, request: Request) -> Response:
        serializer = FamilyMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        repo = DjangoFamilyMemberRepository()
        entity = FamilyMemberEntity(
            id=None,
            user_id=cast("int", request.user.pk),
            name=d["name"],
            role=d["role"],
            color_code=d.get("color_code", "#1976d2"),
            display_order=d.get("display_order", 0),
            include_in_family_total=d.get("include_in_family_total", True),
        )
        saved = repo.save(entity)
        return Response(_member_to_dict(saved), status=status.HTTP_201_CREATED)


class FamilyMemberDetailView(APIView):
    """PUT/DELETE /api/family-members/:id/"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        repo = DjangoFamilyMemberRepository()
        existing = repo.find_by_id(pk, cast("int", request.user.pk))
        if not existing:
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        serializer = FamilyMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        existing.name = d["name"]
        existing.role = d["role"]
        existing.color_code = d.get("color_code", existing.color_code)
        existing.display_order = d.get("display_order", existing.display_order)
        existing.include_in_family_total = d.get("include_in_family_total", existing.include_in_family_total)
        saved = repo.save(existing)
        return Response(_member_to_dict(saved))

    def delete(self, request: Request, pk: int) -> Response:
        repo = DjangoFamilyMemberRepository()
        repo.delete(pk, cast("int", request.user.pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PortfolioAccountListView(APIView):
    """GET /api/portfolio-accounts/  POST /api/portfolio-accounts/"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.portfolios.application.services.import_freshness_service import (
            detect_account_warnings,
        )

        user_id = cast("int", request.user.pk)
        repo = DjangoPortfolioAccountRepository()
        accounts = repo.find_by_user(user_id)

        # 取込漏れ警告のため各口座の最新スナップショットを取得
        snapshot_repo = DjangoAccountSnapshotRepository()
        latest_by_account = {s.account_id: s for s in snapshot_repo.find_latest_by_user(user_id)}
        today = datetime.date.today()

        rows = []
        for a in accounts:
            d = _account_to_dict(a)
            snap = latest_by_account.get(cast("int", a.id))
            d["import_warnings"] = detect_account_warnings(
                asset_class=a.asset_class,
                latest_snapshot_date=snap.snapshot_date if snap else None,
                holdings_count=len(snap.holdings) if snap else 0,
                total_value=float(snap.total_value_jpy) if snap else 0.0,
                as_of_date=today,
            )
            rows.append(d)
        return Response(rows)

    def post(self, request: Request) -> Response:
        serializer = PortfolioAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        # family_member_id の所有権確認
        member_repo = DjangoFamilyMemberRepository()
        member = member_repo.find_by_id(d["family_member_id"], cast("int", request.user.pk))
        if not member:
            return Response({"detail": "家族メンバーが見つかりません"}, status=status.HTTP_400_BAD_REQUEST)
        repo = DjangoPortfolioAccountRepository()
        entity = PortfolioAccountEntity(
            id=None,
            family_member_id=d["family_member_id"],
            institution=d["institution"],
            institution_type=d["institution_type"],
            asset_class=d["asset_class"],
            trading_type=d.get("trading_type", "spot"),
            nickname=d.get("nickname", ""),
            currency=d.get("currency", "JPY"),
            notes=d.get("notes", ""),
            is_active=d.get("is_active", True),
            expected_return_rate=d.get("expected_return_rate"),
            margin_credit_type=d.get("margin_credit_type"),
            margin_interest_rate=d.get("margin_interest_rate"),
        )
        saved = repo.save(entity)
        saved.family_member_name = member.name
        return Response(_account_to_dict(saved), status=status.HTTP_201_CREATED)


class PortfolioAccountDetailView(APIView):
    """PUT/DELETE /api/portfolio-accounts/:id/"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        repo = DjangoPortfolioAccountRepository()
        existing = repo.find_by_id(pk, cast("int", request.user.pk))
        if not existing:
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        serializer = PortfolioAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        existing.institution = d["institution"]
        existing.institution_type = d["institution_type"]
        existing.asset_class = d["asset_class"]
        existing.trading_type = d.get("trading_type", existing.trading_type)
        existing.nickname = d.get("nickname", existing.nickname)
        existing.currency = d.get("currency", existing.currency)
        existing.notes = d.get("notes", existing.notes)
        existing.is_active = d.get("is_active", existing.is_active)
        existing.expected_return_rate = d.get("expected_return_rate", existing.expected_return_rate)
        existing.margin_credit_type = d.get("margin_credit_type", existing.margin_credit_type)
        existing.margin_interest_rate = d.get("margin_interest_rate", existing.margin_interest_rate)
        saved = repo.save(existing)
        return Response(_account_to_dict(saved))

    def delete(self, request: Request, pk: int) -> Response:
        repo = DjangoPortfolioAccountRepository()
        repo.delete(pk, cast("int", request.user.pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountSnapshotListView(APIView):
    """GET /api/portfolio-accounts/:id/snapshots/  POST ..."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, account_id: int) -> Response:
        account_repo = DjangoPortfolioAccountRepository()
        if not account_repo.find_by_id(account_id, cast("int", request.user.pk)):
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        repo = DjangoAccountSnapshotRepository()
        snapshots = repo.find_by_account(account_id, cast("int", request.user.pk))
        return Response([_snapshot_to_dict(s) for s in snapshots])

    def post(self, request: Request, account_id: int) -> Response:
        account_repo = DjangoPortfolioAccountRepository()
        if not account_repo.find_by_id(account_id, cast("int", request.user.pk)):
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        holdings = [
            AccountHoldingEntity(
                id=None,
                snapshot_id=0,
                ticker_code=h.get("ticker_code", ""),
                asset_name=h["asset_name"],
                asset_type=h["asset_type"],
                quantity=h.get("quantity"),
                unit_price=h.get("unit_price"),
                value_jpy=h["value_jpy"],
                cost_jpy=h.get("cost_jpy"),
                stock_id=h.get("stock_id"),
                built_date=h.get("built_date"),
            )
            for h in d.get("holdings", [])
        ]
        entity = AccountSnapshotEntity(
            id=None,
            account_id=account_id,
            snapshot_date=str(d["snapshot_date"]),
            total_value_jpy=d["total_value_jpy"],
            total_cost_jpy=d.get("total_cost_jpy"),
            exchange_rate=d.get("exchange_rate"),
            notes=d.get("notes", ""),
            holdings=holdings,
        )
        repo = DjangoAccountSnapshotRepository()
        saved = repo.save(entity, cast("int", request.user.pk))
        return Response(_snapshot_to_dict(saved), status=status.HTTP_201_CREATED)


class AccountSnapshotDetailView(APIView):
    """PUT/DELETE /api/portfolio-accounts/:id/snapshots/:date/"""

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, account_id: int, snapshot_date: str) -> Response:
        repo = DjangoAccountSnapshotRepository()
        existing = repo.find_by_account_and_date(account_id, snapshot_date, cast("int", request.user.pk))
        if not existing:
            return Response({"detail": "見つかりません"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AccountSnapshotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        holdings = [
            AccountHoldingEntity(
                id=None,
                snapshot_id=existing.id or 0,
                ticker_code=h.get("ticker_code", ""),
                asset_name=h["asset_name"],
                asset_type=h["asset_type"],
                quantity=h.get("quantity"),
                unit_price=h.get("unit_price"),
                value_jpy=h["value_jpy"],
                cost_jpy=h.get("cost_jpy"),
                stock_id=h.get("stock_id"),
                built_date=h.get("built_date"),
            )
            for h in d.get("holdings", [])
        ]
        existing.total_value_jpy = d["total_value_jpy"]
        existing.total_cost_jpy = d.get("total_cost_jpy")
        existing.exchange_rate = d.get("exchange_rate")
        existing.notes = d.get("notes", "")
        existing.holdings = holdings
        saved = repo.save(existing, cast("int", request.user.pk))
        return Response(_snapshot_to_dict(saved))

    def delete(self, request: Request, account_id: int, snapshot_date: str) -> Response:
        repo = DjangoAccountSnapshotRepository()
        repo.delete(account_id, snapshot_date, cast("int", request.user.pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class FamilyPortfolioDashboardView(APIView):
    """GET /api/family-portfolio/dashboard/?view=individual|family

    家族合計・メンバー別集計 + 保有株式の時価評価を統合したダッシュボード。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:  # noqa: C901
        from apps.portfolios.models import PortfolioAccount

        view_mode = request.query_params.get("view", "family")
        user_id = cast("int", request.user.pk)

        member_repo = DjangoFamilyMemberRepository()
        account_repo = DjangoPortfolioAccountRepository()
        snapshot_repo = DjangoAccountSnapshotRepository()

        members = member_repo.find_by_user(user_id)
        accounts = account_repo.find_by_user(user_id)
        latest_snapshots = snapshot_repo.find_latest_by_user(user_id)
        earliest_snapshot_date = snapshot_repo.find_earliest_date_by_user(user_id)

        ac_labels = dict(PortfolioAccount.AssetClass.choices)

        # 口座IDで最新スナップショットをマッピング
        latest_by_account: dict[int, AccountSnapshotEntity] = {s.account_id: s for s in latest_snapshots}

        # self メンバーを特定
        self_member = next((m for m in members if m.role == "self"), None)
        self_member_id = self_member.id if self_member else None

        # individual モード: self メンバーのみ
        if view_mode == "individual":
            target_member_ids = {self_member_id} if self_member_id else set()
        else:
            target_member_ids = {m.id for m in members if m.include_in_family_total and m.id is not None}

        # 口座フィルタリング
        filtered_accounts = [
            acc for acc in accounts if acc.id is not None and acc.family_member_id in target_member_ids
        ]

        # 集計
        total_value = Decimal(0)
        total_cost = Decimal(0)
        latest_date: str | None = None
        by_asset_class: dict[str, Decimal] = {}
        by_account_type: dict[str, Decimal] = {}  # institution_type ベース

        member_map: dict[int, dict[str, Any]] = {}
        for m in members:
            if m.id is None or m.id not in target_member_ids:
                continue
            member_map[m.id] = {
                "member_id": m.id,
                "name": m.name,
                "role": m.role,
                "color_code": m.color_code,
                "total_value_jpy": Decimal(0),
                "total_cost_jpy": Decimal(0),
                "by_asset_class": {},
            }

        account_rows = []
        for acc in filtered_accounts:
            snap = latest_by_account.get(cast("int", acc.id))
            val = snap.total_value_jpy if snap else None
            cost = snap.total_cost_jpy if snap else None
            date_str = snap.snapshot_date if snap else None
            is_margin = acc.trading_type == "margin"

            if val is not None:
                # 信用口座は評価損益のみ資産計上（時価 - 取得原価）
                effective_val = ((val - cost) if cost is not None else Decimal(0)) if is_margin else val

                total_value += effective_val
                if cost is not None and not is_margin:
                    total_cost += cost
                if date_str and (latest_date is None or date_str > latest_date):
                    latest_date = date_str

                # 資産クラス別
                cls = acc.asset_class
                by_asset_class[cls] = by_asset_class.get(cls, Decimal(0)) + effective_val
                # 機関種別
                it = acc.institution_type
                by_account_type[it] = by_account_type.get(it, Decimal(0)) + effective_val

            # メンバー別集計
            m_data = member_map.get(acc.family_member_id)
            if m_data and val is not None:
                effective_val_member = ((val - cost) if cost is not None else Decimal(0)) if is_margin else val
                m_data["total_value_jpy"] += effective_val_member
                if cost is not None and not is_margin:
                    m_data["total_cost_jpy"] += cost
                cls = acc.asset_class
                m_data["by_asset_class"][cls] = m_data["by_asset_class"].get(cls, Decimal(0)) + effective_val_member

            account_rows.append(
                {
                    "id": acc.id,
                    "institution": acc.institution,
                    "nickname": acc.nickname,
                    "institution_type": acc.institution_type,
                    "asset_class": acc.asset_class,
                    "asset_class_display": ac_labels.get(acc.asset_class, acc.asset_class),
                    "trading_type": acc.trading_type,
                    "currency": acc.currency,
                    "member_id": acc.family_member_id,
                    "member_name": acc.family_member_name,
                    "latest_value_jpy": str(val) if val is not None else None,
                    "latest_cost_jpy": str(cost) if cost is not None else None,
                    "latest_date": date_str,
                }
            )

        # ── 動的評価（最新株価で再評価）──
        # 家族合計（total_value）とメンバー別合計（m_data["total_value_jpy"]）のみ動的値で上書き。
        # by_asset_class / by_account_type / by_top_holdings / account_rows は意図的に静的のまま。
        from apps.portfolios.application.services.dynamic_valuation_service import (
            DynamicValuationInput,
        )
        from config import container as di_container

        scope_snapshots = [s for s in latest_snapshots if s.account_id in {a.id for a in filtered_accounts}]
        valuation = di_container.dynamic_portfolio_valuation_service().evaluate(
            DynamicValuationInput(
                accounts=filtered_accounts,
                snapshots=scope_snapshots,
                as_of_date=datetime.date.today(),
            )
        )
        total_value = valuation.total_value
        for m_id, m_data in member_map.items():
            m_data["total_value_jpy"] = valuation.by_member.get(m_id, Decimal(0))

        # stock_holdings_v2: スナップショットから全 holdings を抽出（stock_id があればリアルタイム評価）
        # 米株 (Stock.market_type=='US') の場合、楽天証券 CSV 取込値は USD のため、当日 USD/JPY で
        # JPY 化して返す (フィールド名は *_jpy のままで、unit_price/latest_price も JPY 換算後の値)。
        from apps.portfolios.application.services.fx_conversion_service import FxConversionService
        from apps.stocks.models import Stock

        # 口座IDから口座情報をマッピング
        account_map: dict[int, PortfolioAccountEntity] = {cast("int", a.id): a for a in filtered_accounts}

        # 全ホールディングを収集
        stock_ids_set: set[int] = set()
        raw_stock_holdings: list[tuple[AccountHoldingEntity, int]] = []  # (holding, account_id)
        for snap in latest_snapshots:
            if snap.account_id not in account_map:
                continue
            for h in snap.holdings:
                if h.stock_id is not None:
                    stock_ids_set.add(h.stock_id)
                raw_stock_holdings.append((h, snap.account_id))

        # 最新株価と市場種別を一括取得
        stock_info_map: dict[int, tuple[str, Decimal | None, str]] = {}  # (code, latest_price, market_type)
        if stock_ids_set:
            for s in Stock.objects.filter(pk__in=stock_ids_set).only("id", "code", "latest_price", "market_type"):
                stock_info_map[s.pk] = (s.code, s.latest_price, s.market_type)

        # 当日 USD/JPY (米株保有がある場合のみ取得)
        fx_converter = FxConversionService()
        today_str = datetime.date.today().isoformat()
        usd_jpy_today: Decimal | None = None
        if any(info[2] == "US" for info in stock_info_map.values()):
            usd_jpy_today = fx_converter.get_rate(today_str)

        def _to_jpy(value: Decimal | None, is_us: bool) -> Decimal | None:
            """米株は USD 値を当日 USD/JPY で換算。失敗時は None。"""
            if value is None:
                return None
            if not is_us:
                return value
            if usd_jpy_today is None:
                return None
            return value * usd_jpy_today

        stock_holdings_v2_out: list[dict[str, Any]] = []
        for h, h_acc_id in raw_stock_holdings:
            h_acc = account_map.get(h_acc_id)
            stock_info = stock_info_map.get(cast("int", h.stock_id))
            s_code = stock_info[0] if stock_info else h.ticker_code
            s_price_raw = stock_info[1] if stock_info else None
            is_us = stock_info[2] == "US" if stock_info else False

            # JPY 化
            # unit_price / latest_price は米株の場合 USD 単価で保存されているため USD→JPY 換算が必要。
            # value_jpy / cost_jpy は楽天証券 CSV の「時価評価額」「評価損益[円]」由来で、
            # 米株でも既に JPY 円換算済みの値が入っているため、ここで再換算してはいけない (二重換算バグ防止)。
            unit_price_jpy = _to_jpy(h.unit_price, is_us)
            latest_price_jpy = _to_jpy(s_price_raw, is_us)
            holding_value_jpy = h.value_jpy
            cost_jpy_normalized = h.cost_jpy

            # リアルタイム評価 (常に JPY)
            if latest_price_jpy is not None and h.quantity is not None and h.quantity > 0:
                realtime_value = h.quantity * latest_price_jpy
            elif holding_value_jpy is not None:
                realtime_value = holding_value_jpy
            else:
                realtime_value = Decimal(0)

            stock_holdings_v2_out.append(
                {
                    "stock_id": h.stock_id,
                    "stock_code": s_code,
                    "asset_name": h.asset_name,
                    "ticker_code": h.ticker_code,
                    "asset_type": h.asset_type,
                    "quantity": str(h.quantity) if h.quantity is not None else None,
                    "unit_price": str(unit_price_jpy) if unit_price_jpy is not None else None,
                    "latest_price": str(latest_price_jpy) if latest_price_jpy is not None else None,
                    "value_jpy": str(realtime_value),
                    "cost_jpy": str(cost_jpy_normalized) if cost_jpy_normalized is not None else None,
                    "unrealized_gain_jpy": (
                        str(realtime_value - cost_jpy_normalized) if cost_jpy_normalized is not None else None
                    ),
                    "account_id": h_acc_id,
                    "account_name": (f"{h_acc.institution} {h_acc.nickname}".strip() if h_acc else ""),
                    "member_name": (h_acc.family_member_name if h_acc else ""),
                }
            )

        # 銘柄TOP10（スナップショットの holdings）
        holding_values: list[dict[str, Any]] = []
        for snap in latest_snapshots:
            if snap.account_id not in {a.id for a in filtered_accounts}:
                continue
            for h in snap.holdings:
                holding_values.append({"name": h.asset_name, "value_jpy": h.value_jpy})
        holding_values.sort(key=lambda x: x["value_jpy"], reverse=True)
        top_holdings = holding_values[:10]
        others_value = sum(h["value_jpy"] for h in holding_values[10:])
        if others_value:
            top_holdings.append({"name": "その他", "value_jpy": others_value})
        by_top_holdings = [{"name": h["name"], "value_jpy": str(h["value_jpy"])} for h in top_holdings]

        # メンバー別 by_asset_class を配列に変換
        members_out = []
        for m_data in member_map.values():
            m_data["total_value_jpy"] = str(m_data["total_value_jpy"])
            m_cost = m_data.pop("total_cost_jpy")
            m_data["total_cost_jpy"] = str(m_cost) if m_cost else None
            m_val = Decimal(m_data["total_value_jpy"])
            m_data["unrealized_gain_jpy"] = str(m_val - m_cost) if m_cost else None
            m_data["by_asset_class"] = [
                {"asset_class": k, "label": ac_labels.get(k, k), "value_jpy": str(v)}
                for k, v in m_data["by_asset_class"].items()
            ]
            members_out.append(m_data)

        # 機関種別ラベル
        it_labels = dict(PortfolioAccount.InstitutionType.choices)

        return Response(
            {
                "view": view_mode,
                "total_value_jpy": str(total_value),
                "total_cost_jpy": str(total_cost) if total_cost else None,
                "unrealized_gain_jpy": str(total_value - total_cost) if total_cost else None,
                "latest_snapshot_date": latest_date,
                "earliest_snapshot_date": earliest_snapshot_date,
                "by_member": members_out,
                "by_asset_class": [
                    {"asset_class": k, "label": ac_labels.get(k, k), "value_jpy": str(v)}
                    for k, v in by_asset_class.items()
                ],
                "by_account_type": [
                    {"account_type": k, "label": it_labels.get(k, k), "value_jpy": str(v)}
                    for k, v in by_account_type.items()
                ],
                "by_top_holdings": by_top_holdings,
                "accounts": account_rows,
                "stock_holdings_v2": stock_holdings_v2_out,
            }
        )


def _build_diff(
    existing: AccountSnapshotEntity,
    new_group: Any,
) -> dict[str, Any]:
    """既存スナップショットと新CSVグループの差分を構築する。"""

    # 既存 holdings をキー(ticker_code or asset_name)でマッピング
    old_by_key: dict[str, AccountHoldingEntity] = {}
    for h in existing.holdings:
        key = h.ticker_code if h.ticker_code else h.asset_name
        old_by_key[key] = h

    # 新 holdings をキー(ticker_code or asset_name)でマッピング
    new_keys_seen: set[str] = set()
    holdings_diff: list[dict[str, Any]] = []

    for h in new_group.holdings:
        key = h.ticker_code if h.ticker_code else h.asset_name
        new_keys_seen.add(key)
        old = old_by_key.get(key)

        if old is None:
            holdings_diff.append(
                {
                    "ticker_code": h.ticker_code,
                    "asset_name": h.asset_name,
                    "status": "new",
                    "new_value_jpy": str(h.value_jpy),
                    "old_value_jpy": None,
                    "new_quantity": str(h.quantity),
                    "old_quantity": None,
                }
            )
        else:
            old_val = old.value_jpy
            new_val = h.value_jpy
            old_qty = old.quantity
            new_qty = h.quantity
            changed = old_qty != new_qty or abs(old_val - new_val) > Decimal(1)
            holdings_diff.append(
                {
                    "ticker_code": h.ticker_code,
                    "asset_name": h.asset_name,
                    "status": "changed" if changed else "unchanged",
                    "new_value_jpy": str(new_val),
                    "old_value_jpy": str(old_val),
                    "new_quantity": str(new_qty),
                    "old_quantity": str(old_qty) if old_qty is not None else None,
                }
            )

    # 削除された holdings
    for key, old in old_by_key.items():
        if key not in new_keys_seen:
            holdings_diff.append(
                {
                    "ticker_code": old.ticker_code,
                    "asset_name": old.asset_name,
                    "status": "removed",
                    "new_value_jpy": None,
                    "old_value_jpy": str(old.value_jpy),
                    "new_quantity": None,
                    "old_quantity": str(old.quantity) if old.quantity is not None else None,
                }
            )

    # ソート: changed → new → removed → unchanged
    status_order = {"changed": 0, "new": 1, "removed": 2, "unchanged": 3}
    holdings_diff.sort(key=lambda x: status_order.get(x["status"], 9))

    old_total = existing.total_value_jpy
    new_total = new_group.total_value_jpy
    return {
        "has_existing": True,
        "existing_snapshot_date": existing.snapshot_date,
        "existing_total_value_jpy": str(old_total),
        "value_change_jpy": str(new_total - old_total),
        "holdings_diff": holdings_diff,
    }


class CsvImportView(APIView):
    """POST /api/family-portfolio/import-csv/

    証券会社CSVファイルをインポートしてスナップショットを作成。
    ?preview=true でプレビュー（保存しない）。
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "ファイルが必要です"}, status=status.HTTP_400_BAD_REQUEST)

        provider = request.data.get("provider", "rakuten")
        family_member_id = request.data.get("family_member_id")
        snapshot_date = request.data.get("snapshot_date", "")
        is_preview = request.query_params.get("preview", "false").lower() == "true"

        # 日付の決定: 指定 > ファイル名から抽出 > 今日
        if not snapshot_date and file.name:
            snapshot_date = extract_date_from_filename(file.name) or ""
        if not snapshot_date:
            snapshot_date = datetime.date.today().isoformat()

        # パース
        try:
            parser = get_csv_parser(provider)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = parser.parse(file, snapshot_date)
        except Exception:
            return Response(
                {"detail": "CSVの解析に失敗しました。ファイル形式を確認してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # プレビューレスポンス
        preview_data: dict[str, Any] = {
            "provider": result.provider,
            "snapshot_date": result.snapshot_date,
            "exchange_rates": {k: str(v) for k, v in result.exchange_rates.items()},
            "account_groups": [
                {
                    "asset_type_raw": g.asset_type_raw,
                    "account_type_raw": g.account_type_raw,
                    "asset_class": g.asset_class,
                    "total_value_jpy": str(g.total_value_jpy),
                    "total_cost_jpy": str(g.total_cost_jpy),
                    "currency": g.currency,
                    "holdings_count": len(g.holdings),
                    "holdings": [
                        {
                            "ticker_code": h.ticker_code,
                            "asset_name": h.asset_name,
                            "asset_type": h.asset_type,
                            "quantity": str(h.quantity),
                            "unit_price": str(h.unit_price) if h.unit_price else None,
                            "currency": h.currency,
                            "value_jpy": str(h.value_jpy),
                            "cost_jpy": str(h.cost_jpy) if h.cost_jpy else None,
                        }
                        for h in g.holdings
                    ],
                }
                for g in result.account_groups
            ],
        }

        if is_preview:
            # 差分プレビュー: family_member_id が指定されていれば既存スナップショットと比較
            if family_member_id:
                user_id_preview = cast("int", request.user.pk)
                member_repo_p = DjangoFamilyMemberRepository()
                member_p = member_repo_p.find_by_id(int(family_member_id), user_id_preview)
                if member_p:
                    account_repo_p = DjangoPortfolioAccountRepository()
                    snapshot_repo_p = DjangoAccountSnapshotRepository()
                    existing_accounts_p = account_repo_p.find_by_user(user_id_preview)
                    provider_labels_p = {
                        "rakuten": "楽天証券",
                        "rakuten_margin": "楽天証券",
                        "rakuten_ideco": "楽天証券",
                        "rakuten_fund": "楽天証券",
                        "rakuten_junior_nisa": "楽天証券",
                        "sbi": "SBI証券",
                        "sbi_portfolio": "SBI証券",
                        "sbi_margin": "SBI証券",
                    }
                    institution_p = provider_labels_p.get(provider, provider)

                    for i, group in enumerate(result.account_groups):
                        matched_acc = next(
                            (
                                a
                                for a in existing_accounts_p
                                if a.family_member_id == member_p.id
                                and a.institution == institution_p
                                and a.asset_class == group.asset_class
                                and a.nickname == group.account_type_raw
                            ),
                            None,
                        )
                        if matched_acc and matched_acc.id is not None:
                            latest_snap = snapshot_repo_p.find_latest_single(matched_acc.id, user_id_preview)
                            if latest_snap:
                                preview_data["account_groups"][i]["diff"] = _build_diff(latest_snap, group)

            return Response(preview_data)

        # ---- 実インポート ----
        if not family_member_id:
            return Response(
                {"detail": "family_member_id が必要です"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = cast("int", request.user.pk)
        member_repo = DjangoFamilyMemberRepository()
        member = member_repo.find_by_id(int(family_member_id), user_id)
        if not member:
            return Response({"detail": "家族メンバーが見つかりません"}, status=status.HTTP_400_BAD_REQUEST)

        provider_labels = {
            "rakuten": "楽天証券",
            "rakuten_margin": "楽天証券",
            "rakuten_ideco": "楽天証券",
            "rakuten_fund": "楽天証券",
            "rakuten_junior_nisa": "楽天証券",
            "sbi": "SBI証券",
            "sbi_portfolio": "SBI証券",
            "sbi_margin": "SBI証券",
        }
        institution = provider_labels.get(provider, provider)

        # iDeCo は機関種別を "ideco" にする
        institution_type = "ideco" if provider == "rakuten_ideco" else "securities_jp"
        # 信用取引CSVは trading_type="margin"
        trading_type = "margin" if provider in ("rakuten_margin", "sbi_margin") else "spot"

        account_repo = DjangoPortfolioAccountRepository()
        snapshot_repo = DjangoAccountSnapshotRepository()
        existing_accounts = account_repo.find_by_user(user_id)

        # ticker_code → stock_id のルックアップマップを構築
        from apps.stocks.models import Stock

        all_ticker_codes = {h.ticker_code for g in result.account_groups for h in g.holdings if h.ticker_code}
        stock_id_map: dict[str, int] = {}
        if all_ticker_codes:
            for s in Stock.objects.filter(code__in=all_ticker_codes).only("id", "code"):
                stock_id_map[s.code] = s.pk

        # 投信 → プロキシETF の自動紐付けは Repository.save() 側で一元的に解決する
        # （stock_id の自動リンクと同じ層。API/コマンド等どの経路でも紐付く）。

        created_count = 0
        updated_count = 0

        for group in result.account_groups:
            # 既存口座のマッチング: (family_member_id, institution, asset_class, nickname)
            # 信用 CSV は parser 側で nickname を「特定信用」「一般信用」形式にしているため、
            # 同じ「特定」nickname の現物口座と区別される。
            nickname = group.account_type_raw
            matched = next(
                (
                    a
                    for a in existing_accounts
                    if a.family_member_id == member.id
                    and a.institution == institution
                    and a.asset_class == group.asset_class
                    and a.nickname == nickname
                ),
                None,
            )

            if matched is None:
                # 口座を新規作成
                account_entity = PortfolioAccountEntity(
                    id=None,
                    family_member_id=cast("int", member.id),
                    institution=institution,
                    institution_type=institution_type,
                    asset_class=group.asset_class,
                    trading_type=trading_type,
                    nickname=nickname,
                    currency=group.currency,
                    notes=f"CSV取込({provider})",
                    is_active=True,
                )
                matched = account_repo.save(account_entity)

            # スナップショット作成
            holdings = [
                AccountHoldingEntity(
                    id=None,
                    snapshot_id=0,
                    ticker_code=h.ticker_code,
                    asset_name=h.asset_name,
                    asset_type=h.asset_type,
                    quantity=h.quantity,
                    unit_price=h.unit_price,
                    value_jpy=h.value_jpy,
                    cost_jpy=h.cost_jpy,
                    stock_id=stock_id_map.get(h.ticker_code),
                )
                for h in group.holdings
            ]

            # 為替レートの取得
            exchange_rate: Decimal | None = None
            if group.currency == "USD":
                exchange_rate = result.exchange_rates.get("USD")

            snapshot_entity = AccountSnapshotEntity(
                id=None,
                account_id=cast("int", matched.id),
                snapshot_date=result.snapshot_date,
                total_value_jpy=group.total_value_jpy,
                total_cost_jpy=group.total_cost_jpy if group.total_cost_jpy else None,
                exchange_rate=exchange_rate,
                notes=f"CSV取込({provider})",
                holdings=holdings,
            )

            existing_snap = snapshot_repo.find_by_account_and_date(
                cast("int", matched.id),
                result.snapshot_date,
                user_id,
            )
            if existing_snap:
                snapshot_entity.id = existing_snap.id
                updated_count += 1
            else:
                created_count += 1

            snapshot_repo.save(snapshot_entity, user_id)

        return Response(
            {
                "message": f"インポート完了: {created_count}件作成, {updated_count}件更新",
                "created_count": created_count,
                "updated_count": updated_count,
                "preview": preview_data,
            },
            status=status.HTTP_201_CREATED,
        )


def _watchlist_to_dict(
    entity: WatchlistItemEntity,
    screening_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": entity.id,
        "stock_code": entity.stock_code,
        "stock_name": entity.stock_name,
        "memo": entity.memo,
    }
    if screening_map is not None:
        sr = screening_map.get(entity.stock_code)
        if sr is not None:

            def _s(v: object) -> str | None:
                return str(v) if v is not None else None

            base.update(
                {
                    "latest_price": _s(sr.latest_price),
                    "fair_value": _s(sr.fair_value),
                    "discount_rate": _s(sr.discount_rate),
                    "evaluation_zone": sr.evaluation_zone,
                    "growth_rate_label": sr.growth_rate_label,
                    "eps_growth_yoy": _s(sr.eps_growth_yoy),
                    "eps_cagr_3y": _s(sr.eps_cagr_3y),
                    "roe_trend": sr.roe_trend,
                    "sl_ratio": _s(sr.sl_ratio),
                    "dividend_yield": _s(sr.dividend_yield),
                    "consecutive_dividend_years": sr.consecutive_dividend_years,
                    "progressive_dividend_years": sr.progressive_dividend_years,
                    "is_owner_managed": sr.is_owner_managed,
                }
            )
    return base


class WatchlistListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.stocks.application.usecases.screening_usecase import ScreeningUseCase
        from config.container import financial_repository, margin_repository, stock_repository

        repo = DjangoWatchlistRepository()
        items = repo.find_by_user(cast("int", request.user.pk))

        # スクリーニングデータを取得してウォッチリスト銘柄にマージ
        screening_map: dict[str, Any] = {}
        if items:
            usecase = ScreeningUseCase(
                stock_repo=stock_repository(),
                financial_repo=financial_repository(),
                margin_repo=margin_repository(),
            )
            results = usecase.execute(growth_rate=Decimal("0.02"))
            watched_codes = {item.stock_code for item in items}
            screening_map = {r.code: r for r in results if r.code in watched_codes}

        data = [_watchlist_to_dict(item, screening_map) for item in items]
        return Response(data)

    def post(self, request: Request) -> Response:
        serializer = WatchlistItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        repo = DjangoWatchlistRepository()
        entity = WatchlistItemEntity(
            id=None,
            user_id=cast("int", request.user.pk),
            stock_id=0,
            stock_code=serializer.validated_data["stock_code"],
            memo=serializer.validated_data.get("memo", ""),
        )
        try:
            item = repo.add(entity)
        except Exception:
            return Response(
                {"detail": "銘柄が見つかりません"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            WatchlistItemSerializer(_watchlist_to_dict(item)).data,
            status=status.HTTP_201_CREATED,
        )


class ShareDashboardView(APIView):
    """GET /api/family-portfolio/share-dashboard/

    X共有用ダッシュボード。個人情報なし + 前月対比 + 前日対比 + 当月日次推移。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:  # noqa: C901
        from apps.portfolios.models import PortfolioAccount
        from apps.stocks.models import Stock, StockPrice

        user_id = cast("int", request.user.pk)
        today = datetime.date.today()

        member_repo = DjangoFamilyMemberRepository()
        account_repo = DjangoPortfolioAccountRepository()
        snapshot_repo = DjangoAccountSnapshotRepository()

        members = member_repo.find_by_user(user_id)
        accounts = account_repo.find_by_user(user_id)
        latest_snapshots = snapshot_repo.find_latest_by_user(user_id)
        all_snapshots = snapshot_repo.find_all_by_user(user_id)

        ac_labels = dict(PortfolioAccount.AssetClass.choices)

        # メンバー絞り込み（?member=<id> or 省略=家族合計）
        member_param = request.query_params.get("member")
        if member_param and member_param != "all":
            try:
                selected_member_id = int(member_param)
                target_member_ids = {selected_member_id}
            except ValueError:
                target_member_ids = {m.id for m in members if m.include_in_family_total and m.id is not None}
        else:
            target_member_ids = {m.id for m in members if m.include_in_family_total and m.id is not None}

        selected_member = (
            next((m for m in members if m.id in target_member_ids), None) if len(target_member_ids) == 1 else None
        )

        filtered_accounts = [
            acc for acc in accounts if acc.id is not None and acc.family_member_id in target_member_ids
        ]
        account_ids = {cast("int", acc.id) for acc in filtered_accounts}
        latest_by_account = {s.account_id: s for s in latest_snapshots if s.account_id in account_ids}

        # スコープ内スナップショットの最古日（年率損益計算用）
        scope_snapshot_dates = [s.snapshot_date for s in all_snapshots if s.account_id in account_ids]
        earliest_snapshot_date = min(scope_snapshot_dates) if scope_snapshot_dates else None

        # ── 動的評価（最新株価で再評価） ──
        # total_value と by_asset_class は動的評価サービスで算出する。
        # total_cost / latest_date はスナップショット時点の静的値で集計する。
        from apps.portfolios.application.services.dynamic_valuation_service import (
            DynamicValuationInput,
        )
        from config import container as di_container

        scope_snapshots = [s for s in latest_snapshots if s.account_id in account_ids]
        valuation = di_container.dynamic_portfolio_valuation_service().evaluate(
            DynamicValuationInput(
                accounts=filtered_accounts,
                snapshots=scope_snapshots,
                as_of_date=today,
            )
        )
        total_value = valuation.total_value
        by_asset_class = valuation.by_asset_class

        total_cost = Decimal(0)
        has_cost = False
        latest_date: str | None = None

        # 信用/現物判定マップ（後段の DoD/YoY 計算で使用）
        acc_trading: dict[int, str] = {}
        acc_asset_class: dict[int, str] = {}
        for acc in filtered_accounts:
            acc_trading[cast("int", acc.id)] = acc.trading_type
            acc_asset_class[cast("int", acc.id)] = acc.asset_class

        # total_cost / has_cost / latest_date のみ静的集計
        for acc in filtered_accounts:
            snap = latest_by_account.get(cast("int", acc.id))
            if snap is None:
                continue
            cost = snap.total_cost_jpy
            is_margin = acc.trading_type == "margin"
            # 取得原価: 現物口座のみ（信用は損益のみが資産額なのでcost不要）
            if not is_margin and cost is not None:
                total_cost += cost
                has_cost = True
            if snap.snapshot_date and (latest_date is None or snap.snapshot_date > latest_date):
                latest_date = snap.snapshot_date

        # ── 株式保有を収集（DoD + 月次チャート用）──
        # 現物: qty × price で日次再計算
        stock_holdings: list[tuple[int, Decimal, int]] = []  # (stock_id, quantity, account_id)
        # 信用: qty × price - cost（損益）で日次再計算
        margin_stock_holdings: list[tuple[int, Decimal, Decimal, int]] = []  # (stock_id, qty, cost, acc_id)
        # 投信プロキシ: snapshot_value × (proxy_price / ref_price) で変動率近似
        fund_holdings: list[tuple[int, Decimal, str]] = []  # (proxy_stock_id, snapshot_value, snapshot_date)
        non_stock_value = Decimal(0)  # 株式以外の固定部分

        for acc in filtered_accounts:
            snap = latest_by_account.get(cast("int", acc.id))
            if snap is None:
                continue
            is_margin = acc.trading_type == "margin"
            val = snap.total_value_jpy
            cost = snap.total_cost_jpy
            effective = ((val - cost) if cost is not None else Decimal(0)) if is_margin else val

            if is_margin:
                margin_stock_pnl_snapshot = Decimal(0)
                for h in snap.holdings:
                    if h.stock_id is not None and h.quantity is not None and h.quantity > 0:
                        h_cost = h.cost_jpy if h.cost_jpy is not None else Decimal(0)
                        margin_stock_holdings.append((h.stock_id, h.quantity, h_cost, snap.account_id))
                        margin_stock_pnl_snapshot += h.value_jpy - h_cost
                # 信用口座のうち株式以外の固定部分
                non_stock_value += effective - margin_stock_pnl_snapshot
            else:
                stock_value_in_account = Decimal(0)
                for h in snap.holdings:
                    if h.stock_id is not None and h.quantity is not None and h.quantity > 0:
                        stock_holdings.append((h.stock_id, h.quantity, snap.account_id))
                        stock_value_in_account += h.value_jpy
                    elif h.proxy_stock_id is not None:
                        fund_holdings.append((h.proxy_stock_id, h.value_jpy, snap.snapshot_date))
                        stock_value_in_account += h.value_jpy
                # 口座の total から株式・投信分を引いた残り（現金等）を non_stock に加算
                non_stock_value += effective - stock_value_in_account

        # ── 株価一括取得（当月分 + 前月末）──
        fund_proxy_ids = {pid for pid, _, _ in fund_holdings}
        stock_ids = (
            {sid for sid, _, _ in stock_holdings} | {sid for sid, _, _, _ in margin_stock_holdings} | fund_proxy_ids
        )
        month_start = today.replace(day=1)
        price_map: dict[int, dict[str, Decimal]] = {}  # stock_id → {date_str → price}

        if stock_ids:
            # プロキシETF用: スナップショット日が月初より前の場合を考慮し余裕を持つ
            from_date = month_start - datetime.timedelta(days=40)
            for sid, price_date, price in StockPrice.objects.filter(
                stock_id__in=stock_ids,
                date__gte=from_date,
                date__lte=today,
            ).values_list("stock_id", "date", "close_price"):
                price_map.setdefault(sid, {})[str(price_date)] = price

        # 最新株価（Stock.latest_price）と market_type を取得
        latest_price_map: dict[int, Decimal] = {}
        market_type_map: dict[int, str] = {}
        if stock_ids:
            for stk in Stock.objects.filter(pk__in=stock_ids).only("id", "latest_price", "market_type"):
                if stk.latest_price is not None:
                    latest_price_map[stk.pk] = stk.latest_price
                market_type_map[stk.pk] = stk.market_type

        # FX 換算サービス（米株を JPY 化するため）
        from apps.portfolios.application.services.fx_conversion_service import FxConversionService

        fx_converter = FxConversionService()

        def _get_price(stock_id: int, date_str: str) -> Decimal | None:
            """株価取得（前方補完あり）。市場通貨のまま返す。"""
            prices = price_map.get(stock_id, {})
            price = prices.get(date_str)
            if price is None:
                earlier = [d for d in prices if d <= date_str]
                price = prices[max(earlier)] if earlier else latest_price_map.get(stock_id)
            return price

        def _get_price_jpy(stock_id: int, date_str: str) -> Decimal | None:
            """株価を JPY に正規化して返す。米株は指定日の USD/JPY を掛ける。"""
            price = _get_price(stock_id, date_str)
            if price is None:
                return None
            if market_type_map.get(stock_id) == "US":
                rate = fx_converter.get_rate(date_str)
                if rate is None:
                    return None
                return price * rate
            return price

        def _calc_stock_total(date_str: str) -> Decimal:
            """指定日の株式保有総額を計算（現物 + 信用損益 + 投信プロキシ、すべて JPY）"""
            result = Decimal(0)
            # 現物: qty × price_jpy
            for sid, qty, _ in stock_holdings:
                price_jpy = _get_price_jpy(sid, date_str)
                if price_jpy is not None:
                    result += qty * price_jpy
            # 信用: qty × price_jpy - cost（損益）。cost は CSV 取込時に JPY 換算済み
            for sid, qty, h_cost, _ in margin_stock_holdings:
                price_jpy = _get_price_jpy(sid, date_str)
                if price_jpy is not None:
                    result += qty * price_jpy - h_cost
            # 投信プロキシ: snapshot_value × (proxy_price / ref_price)
            # - 米株 proxy (VTI 等) を使うため JPY 化必須 (USD のままだと _get_price のフォールバックで
            #   latest_price_map → 異常な比率になり MTD 暴走する事故あり、2026-05-27)
            # - ref/cur が両方 JPY なら比率も意味を持つ
            # - 比率が極端 (snap_date のデータが無くフォールバック値が混ざる) なら固定値で安全側に
            for proxy_id, snap_value, snap_date in fund_holdings:
                ref_price_jpy = _get_price_jpy(proxy_id, snap_date)
                cur_price_jpy = _get_price_jpy(proxy_id, date_str)
                if ref_price_jpy and cur_price_jpy and ref_price_jpy > 0:
                    ratio = cur_price_jpy / ref_price_jpy
                    # 月次チャート用途で 1 ヶ月以内の比率なので [0.5, 2.0] を妥当範囲とする
                    if Decimal("0.5") <= ratio <= Decimal("2.0"):
                        result += snap_value * ratio
                    else:
                        result += snap_value  # 比率異常 → 固定値
                else:
                    result += snap_value  # フォールバック: 固定値
            return result

        # ── 当月日次チャート ──
        # 取引日を抽出（StockPriceに存在する日付）
        trading_dates: set[str] = set()
        for prices in price_map.values():
            trading_dates.update(prices.keys())

        chart_dates: list[str]
        if trading_dates:
            # 前月末最終営業日 + 当月の営業日
            prev_month_dates = sorted(d for d in trading_dates if d < str(month_start))
            current_month_dates = sorted(d for d in trading_dates if d >= str(month_start))
            chart_dates = (prev_month_dates[-1:]) + current_month_dates
        elif non_stock_value > 0:
            # 株式保有なし: スナップショット日 + 今日をチャート日付として使用
            snap_dates_in_month: set[str] = set()
            for s in all_snapshots:
                if s.account_id not in account_ids:
                    continue
                if s.snapshot_date >= str(month_start) and s.snapshot_date <= str(today):
                    snap_dates_in_month.add(s.snapshot_date)
            snap_dates_in_month.add(str(today))
            chart_dates = sorted(snap_dates_in_month)
        else:
            chart_dates = []

        monthly_chart: list[dict[str, Any]] = []
        for d in chart_dates:
            stock_total = _calc_stock_total(d)
            daily_total = int(non_stock_value + stock_total)
            # value: 全資産 (現金/保険/共済等を含む)、stock_value: 株式系のみ。
            # frontend で「月初来パフォーマンス %」を株式分母で計算する用 (カビュー寄せ)。
            monthly_chart.append({"date": d, "value": daily_total, "stock_value": int(stock_total)})

        # ── 月初来 baseline (前月末日時点の総資産) ──
        # baseline = 前月末日 (カレンダー上の最終日) 時点の holdings × 前月末日の株価で再評価。
        # これにより 6/1 0時 時点の評価 = baseline、その後の変動 (土日含む) はすべて
        # MTD に含まれる。
        #   - 6/1 朝 → MTD ≈ ¥0 近傍 (前月末から評価変動なし)
        #   - 6/2 終値後 → MTD = 6/1 + 6/2 のリターン
        # baseline_date は monthly_chart[0].date (前月末営業日) ではなく、
        # 当月初日の前日 (= 前月末日) 固定で計算する。
        # current (total_value) と同じ DynamicValuationService 評価方式で揃え、
        # 評価方式の非対称性を排除する。
        # 詳細: docs/reports/2026-05-29_mtd_remediation_plan.md (Step 1.7)
        monthly_chart_total_baseline: int | None = None
        baseline_date = today.replace(day=1) - datetime.timedelta(days=1)
        baseline_date_str = baseline_date.isoformat()
        # 月初日以前の最新スナップショットを各口座について取得 (holdings 込み)
        baseline_snapshots = snapshot_repo.find_each_account_latest_before(
            user_id, baseline_date_str, with_holdings=True
        )
        baseline_snapshots_filtered = [s for s in baseline_snapshots if s.account_id in account_ids]
        if baseline_snapshots_filtered:
            # 月初時点 holdings を月初日の株価で動的再評価
            baseline_valuation = di_container.dynamic_portfolio_valuation_service().evaluate(
                DynamicValuationInput(
                    accounts=filtered_accounts,
                    snapshots=baseline_snapshots_filtered,
                    as_of_date=baseline_date,
                )
            )
            monthly_chart_total_baseline = int(baseline_valuation.total_value)

        # ── 指数ベンチマーク（正規化）──
        index_etfs = {
            "nikkei225": "1321",
            "topix": "1306",
            "nasdaq100": "1545",
            "sp500": "1557",
        }
        if monthly_chart and len(monthly_chart) >= 2:
            base_value = monthly_chart[0]["value"]
            idx_stock_map: dict[str, int] = {}
            for key, code in index_etfs.items():
                try:
                    stk = Stock.objects.only("id").get(code=code)
                    idx_stock_map[key] = stk.pk
                except Stock.DoesNotExist:
                    pass

            if idx_stock_map:
                idx_price_map: dict[int, dict[str, Decimal]] = {}
                # ref が見つからずに空ループするのを避けるため、現物保有側 (40 日窓) と揃える
                idx_from = month_start - datetime.timedelta(days=40)
                for sid, price_date, price in StockPrice.objects.filter(
                    stock_id__in=idx_stock_map.values(),
                    date__gte=idx_from,
                    date__lte=today,
                ).values_list("stock_id", "date", "close_price"):
                    idx_price_map.setdefault(sid, {})[str(price_date)] = price

                # 月次チャートで指数が ±50% 動くことはまずないため、バンド外の比率は描画から除外する。
                # 異常 close_price (株式分割未反映 / yfinance のスパイク / ゼロ等) を防御する。
                ratio_min = Decimal("0.7")
                ratio_max = Decimal("1.5")

                first_date = monthly_chart[0]["date"]
                idx_code_map = {key: code for key, code in index_etfs.items() if key in idx_stock_map}
                for key, sid in idx_stock_map.items():
                    prices = idx_price_map.get(sid, {})
                    # 基準日の価格（前方補完）
                    ref = prices.get(first_date)
                    if ref is None:
                        earlier = [dd for dd in prices if dd <= first_date]
                        ref = prices[max(earlier)] if earlier else None
                    if ref is None or ref <= 0:
                        continue
                    for pt in monthly_chart:
                        p = prices.get(pt["date"])
                        if p is None:
                            earlier = [dd for dd in prices if dd <= pt["date"]]
                            p = prices[max(earlier)] if earlier else None
                        if p is None:
                            continue
                        ratio = p / ref
                        if not (ratio_min <= ratio <= ratio_max):
                            logger.warning(
                                "index proxy anomaly skipped: key=%s code=%s date=%s p=%s ref=%s ratio=%s",
                                key,
                                idx_code_map.get(key),
                                pt["date"],
                                p,
                                ref,
                                ratio,
                            )
                            continue
                        pt[key] = int(base_value * ratio)

        # ── 前年対比 ──
        yoy_change_jpy: str | None = None
        yoy_change_pct: str | None = None

        # 1年前時点の口座合計を算出（1年前以前の最新スナップショットで補完）
        one_year_ago = str(today - datetime.timedelta(days=365))
        yoy_snap_date: dict[int, str] = {}
        yoy_snap_value: dict[int, Decimal] = {}
        for s in all_snapshots:
            if s.account_id not in account_ids:
                continue
            if s.snapshot_date > one_year_ago:
                continue
            prev_date = yoy_snap_date.get(s.account_id, "")
            if s.snapshot_date > prev_date:
                is_margin = acc_trading.get(s.account_id, "spot") == "margin"
                val = s.total_value_jpy
                cost = s.total_cost_jpy
                effective = ((val - cost) if cost is not None else Decimal(0)) if is_margin else val
                yoy_snap_value[s.account_id] = effective
                yoy_snap_date[s.account_id] = s.snapshot_date

        if yoy_snap_value:
            yoy_total = sum(yoy_snap_value.values())
            diff = total_value - yoy_total
            pct = (diff / yoy_total * 100) if yoy_total else Decimal(0)
            yoy_change_jpy = str(int(diff))
            yoy_change_pct = str(round(pct, 2))

        # ── 前日対比 ──
        dod_change_jpy: str | None = None
        dod_change_pct: str | None = None

        if monthly_chart and len(monthly_chart) >= 2:
            yesterday_total = Decimal(monthly_chart[-2]["value"])
            today_total = Decimal(monthly_chart[-1]["value"])
            dod_diff = today_total - yesterday_total
            dod_pct = (dod_diff / yesterday_total * 100) if yesterday_total else Decimal(0)
            dod_change_jpy = str(int(dod_diff))
            dod_change_pct = str(round(dod_pct, 2))
        elif stock_ids:
            # チャートデータが不十分な場合のフォールバック
            yesterday = today - datetime.timedelta(days=1)
            yesterday_stock = _calc_stock_total(str(yesterday))
            today_stock = _calc_stock_total(str(today))
            yesterday_total = non_stock_value + yesterday_stock
            today_total_calc = non_stock_value + today_stock
            if yesterday_total > 0:
                dod_diff = today_total_calc - yesterday_total
                dod_pct = dod_diff / yesterday_total * 100
                dod_change_jpy = str(int(dod_diff))
                dod_change_pct = str(round(dod_pct, 2))
        elif not stock_ids and non_stock_value > 0:
            # 株式なし: 前日対比は0（日次変動なし）
            dod_change_jpy = "0"
            dod_change_pct = "0.00"

        # ── 取込漏れ警告の集計 ──
        # 共有ダッシュボードは匿名のため口座名は出さず、警告種別ごとの口座数のみ返す。
        # データの正確性（明細欠落/更新停止で日次変動が反映されない口座がある）を示す。
        from apps.portfolios.application.services.import_freshness_service import (
            detect_account_warnings,
        )

        warning_counts: dict[str, int] = {}
        for acc in filtered_accounts:
            snap = latest_by_account.get(cast("int", acc.id))
            for w in detect_account_warnings(
                asset_class=acc.asset_class,
                latest_snapshot_date=snap.snapshot_date if snap else None,
                holdings_count=len(snap.holdings) if snap else 0,
                total_value=float(snap.total_value_jpy) if snap else 0.0,
                as_of_date=today,
            ):
                warning_counts[w] = warning_counts.get(w, 0) + 1

        # ── レスポンス ──
        return Response(
            {
                "label": selected_member.name if selected_member else "家族合計",
                "total_value_jpy": str(int(total_value)),
                "total_cost_jpy": str(int(total_cost)) if has_cost else None,
                "unrealized_gain_jpy": str(int(total_value - total_cost)) if has_cost else None,
                "latest_snapshot_date": latest_date,
                "earliest_snapshot_date": earliest_snapshot_date,
                "yoy_change_jpy": yoy_change_jpy,
                "yoy_change_pct": yoy_change_pct,
                "dod_change_jpy": dod_change_jpy,
                "dod_change_pct": dod_change_pct,
                "by_asset_class": [
                    {"asset_class": cls, "label": ac_labels.get(cls, cls), "value_jpy": str(int(v))}
                    for cls, v in sorted(by_asset_class.items(), key=lambda x: x[1], reverse=True)
                    if v > 0
                ],
                "monthly_chart": monthly_chart,
                "monthly_chart_total_baseline": (
                    str(monthly_chart_total_baseline) if monthly_chart_total_baseline is not None else None
                ),
                "monthly_chart_total_current": str(int(total_value)),
                "import_warning_counts": warning_counts,
            }
        )


class FamilyPortfolioHistoryView(APIView):
    """GET /api/family-portfolio/history/?period=1y

    家族合計＋メンバー別の資産推移を返す。
    """

    permission_classes = [IsAuthenticated]

    _PERIOD_MONTHS: dict[str, int | None] = {
        "6m": 6,
        "1y": 12,
        "3y": 36,
        "all": None,
    }

    def get(self, request: Request) -> Response:
        user_id = cast("int", request.user.pk)
        period = request.query_params.get("period", "1y")
        months = self._PERIOD_MONTHS.get(period)

        member_repo = DjangoFamilyMemberRepository()
        account_repo = DjangoPortfolioAccountRepository()
        snapshot_repo = DjangoAccountSnapshotRepository()

        members = member_repo.find_by_user(user_id)
        accounts = account_repo.find_by_user(user_id)
        all_snapshots = snapshot_repo.find_all_by_user(user_id)

        if not all_snapshots:
            return Response({"period": period, "members": [], "history": []})

        # 対象メンバー（include_in_family_total のみ）
        target_member_ids = {m.id for m in members if m.include_in_family_total and m.id is not None}

        # 口座 → メンバー マッピング、口座 → 信用フラグ
        account_member_map: dict[int, int] = {}
        account_is_margin: dict[int, bool] = {}
        for acc in accounts:
            if acc.id is not None and acc.family_member_id in target_member_ids:
                account_member_map[acc.id] = acc.family_member_id
                account_is_margin[acc.id] = acc.trading_type == "margin"

        # 対象スナップショットのみ
        filtered_snapshots = [s for s in all_snapshots if s.account_id in account_member_map]
        if not filtered_snapshots:
            return Response({"period": period, "members": [], "history": []})

        # 全日付を収集
        all_dates = sorted({s.snapshot_date for s in filtered_snapshots})

        # 期間フィルタ
        if months is not None:
            cutoff = (datetime.date.today() - datetime.timedelta(days=months * 30)).isoformat()
            all_dates = [d for d in all_dates if d >= cutoff]

        if not all_dates:
            return Response({"period": period, "members": [], "history": []})

        # 口座ごとの日付→金額マップ（信用は val-cost、現物は val）
        account_date_value: dict[int, dict[str, Decimal]] = {}
        for s in filtered_snapshots:
            is_margin = account_is_margin.get(s.account_id, False)
            eff = _effective_account_value(s.total_value_jpy, s.total_cost_jpy, is_margin)
            account_date_value.setdefault(s.account_id, {})[s.snapshot_date] = eff

        # 各日付で前方補完して集計
        history: list[dict[str, object]] = []
        # 口座ごとの「直近の既知値」を保持
        last_known: dict[int, Decimal] = {}

        for date in all_dates:
            member_totals: dict[int, Decimal] = {}
            for acc_id, member_id in account_member_map.items():
                values = account_date_value.get(acc_id, {})
                if date in values:
                    last_known[acc_id] = values[date]
                val = last_known.get(acc_id, Decimal(0))
                member_totals[member_id] = member_totals.get(member_id, Decimal(0)) + val

            total = int(sum(member_totals.values()))
            members_dict = {str(mid): int(val) for mid, val in member_totals.items() if val > 0}
            history.append({"date": date, "total": total, "members": members_dict})

        # メンバー情報
        member_info = [
            {"id": m.id, "name": m.name, "color_code": m.color_code} for m in members if m.id in target_member_ids
        ]

        return Response({"period": period, "members": member_info, "history": history})


class WatchlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, stock_code: str) -> Response:
        repo = DjangoWatchlistRepository()
        repo.remove(cast("int", request.user.pk), stock_code)
        return Response(status=status.HTTP_204_NO_CONTENT)
