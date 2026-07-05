"""月初来損益 (MTD) 計算の診断ツール。

ダッシュボード月間成績の `+¥XXX (+YY%)` が異常になったときに、原因を一発で
特定するための診断コマンド。修正方針書 (docs/reports/2026-05-29_mtd_remediation_plan.md)
の 6 つの診断クエリを実装。

実行例:
    docker compose exec backend uv run python manage.py diagnose_mtd
    docker compose exec backend uv run python manage.py diagnose_mtd --member-id 1
"""

from __future__ import annotations

import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Count, Sum

from apps.portfolios.models import (
    AccountHolding,
    AccountSnapshot,
    FamilyMember,
    PortfolioAccount,
)
from apps.stocks.models import StockPrice


class Command(BaseCommand):
    help = "月初来損益 (MTD) 計算の診断: 投信紐付け状況 / chart_dates / asset_class 集計を出力"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--member-id",
            type=int,
            default=None,
            help="特定の FamilyMember.id に絞って診断 (省略時は家族合算)",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="特定の auth_user.id に絞って診断 (省略時は全ユーザー)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        member_id: int | None = options.get("member_id")
        user_id: int | None = options.get("user_id")

        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.MIGRATE_HEADING("MTD 診断レポート"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

        # フィルタ構築
        holding_filter: dict[str, Any] = {}
        account_filter: dict[str, Any] = {}
        if user_id is not None:
            account_filter["family_member__user_id"] = user_id
            holding_filter["snapshot__account__family_member__user_id"] = user_id
            self.stdout.write(f"対象ユーザー: user_id={user_id}")
        if member_id is not None:
            account_filter["family_member_id"] = member_id
            holding_filter["snapshot__account__family_member_id"] = member_id
            member = FamilyMember.objects.filter(pk=member_id).first()
            self.stdout.write(f"対象メンバー: {member.name if member else f'id={member_id}'}")
        self.stdout.write("")

        self._diag_1_unlinked_funds(holding_filter)
        self._diag_2_fund_link_distribution(holding_filter)
        self._diag_3_unlinked_fund_names(holding_filter)
        self._diag_4_chart_dates_baseline()
        self._diag_5_asset_class_breakdown(account_filter)
        self._diag_6_share_dashboard_internals(member_id=member_id, user_id=user_id)

        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write("診断完了")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

    # ============================================================
    # 診断 1: 未紐付け投信件数と総評価額
    # ============================================================
    def _diag_1_unlinked_funds(self, holding_filter: dict[str, Any]) -> None:
        self.stdout.write(self.style.NOTICE("\n[診断 1] 未紐付け投信 (stock_id=NULL かつ proxy_stock_id=NULL)"))
        unlinked = AccountHolding.objects.filter(
            asset_type="fund",
            stock_id__isnull=True,
            proxy_stock_id__isnull=True,
            **holding_filter,
        )
        result = unlinked.aggregate(cnt=Count("id"), total=Sum("value_jpy"))
        cnt = result["cnt"] or 0
        total = result["total"] or 0
        self.stdout.write(f"  件数: {cnt}")
        self.stdout.write(f"  総評価額: ¥{int(total):,}")
        if cnt > 0:
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠️ MTD 計算で取りこぼされる投信あり。link_fund_proxies の実行 or Step 2 修正を検討"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ 未紐付け投信なし"))

    # ============================================================
    # 診断 2: 投信の紐付け状況分布
    # ============================================================
    def _diag_2_fund_link_distribution(self, holding_filter: dict[str, Any]) -> None:
        self.stdout.write(self.style.NOTICE("\n[診断 2] 投信の紐付け状況分布"))
        fund = AccountHolding.objects.filter(asset_type="fund", **holding_filter)
        total = fund.count()
        with_stock = fund.filter(stock_id__isnull=False).count()
        with_proxy = fund.filter(proxy_stock_id__isnull=False).count()
        both_null = fund.filter(stock_id__isnull=True, proxy_stock_id__isnull=True).count()
        self.stdout.write(f"  total              : {total}")
        self.stdout.write(f"  with_stock_id      : {with_stock}")
        self.stdout.write(f"  with_proxy_stock_id: {with_proxy}")
        self.stdout.write(f"  both_null (取りこぼし対象): {both_null}")

    # ============================================================
    # 診断 3: 未紐付け投信の asset_name 一覧
    # ============================================================
    def _diag_3_unlinked_fund_names(self, holding_filter: dict[str, Any]) -> None:
        self.stdout.write(self.style.NOTICE("\n[診断 3] 未紐付け投信の asset_name 一覧 (FUND_PROXY_MAP 追加候補)"))
        names = (
            AccountHolding.objects.filter(
                asset_type="fund",
                stock_id__isnull=True,
                proxy_stock_id__isnull=True,
                **holding_filter,
            )
            .values_list("asset_name", flat=True)
            .distinct()
        )
        if not names:
            self.stdout.write(self.style.SUCCESS("  (該当なし)"))
            return
        for name in names:
            self.stdout.write(f"  - {name}")

    # ============================================================
    # 診断 4: chart_dates[0] の確定
    # ============================================================
    def _diag_4_chart_dates_baseline(self) -> None:
        self.stdout.write(self.style.NOTICE("\n[診断 4] chart_dates[0] 候補 (前月末営業日)"))
        today = datetime.date.today()
        month_start = today.replace(day=1)
        from_date = month_start - datetime.timedelta(days=40)
        prev = StockPrice.objects.filter(date__lt=month_start, date__gte=from_date).order_by("-date").first()
        self.stdout.write(f"  検索範囲: {from_date} 〜 {month_start} (40 日窓)")
        if prev:
            self.stdout.write(self.style.SUCCESS(f"  ✓ 前月末営業日: {prev.date}"))
        else:
            self.stdout.write(
                self.style.WARNING("  ⚠️ 40 日窓内に株価データなし → chart_dates[0] が当月初日にスライドする可能性")
            )

    # ============================================================
    # 診断 5: asset_class 別評価額 (カビュー比較用)
    # ============================================================
    def _diag_5_asset_class_breakdown(self, account_filter: dict[str, Any]) -> None:
        self.stdout.write(self.style.NOTICE("\n[診断 5] 最新スナップショットの asset_class 別評価額"))
        ac_labels = dict(PortfolioAccount.AssetClass.choices)

        accounts = PortfolioAccount.objects.filter(is_active=True, **account_filter)
        breakdown: dict[str, int] = {}
        for acc in accounts:
            latest = AccountSnapshot.objects.filter(account_id=acc.id).order_by("-snapshot_date").first()
            if latest is None:
                continue
            breakdown.setdefault(acc.asset_class, 0)
            breakdown[acc.asset_class] += int(latest.total_value_jpy)

        if not breakdown:
            self.stdout.write("  (スナップショットなし)")
            return

        total = sum(breakdown.values())
        for cls, value in sorted(breakdown.items(), key=lambda x: -x[1]):
            label = ac_labels.get(cls, cls)
            pct = (value / total * 100) if total else 0
            self.stdout.write(f"  {label:14s}: ¥{value:>15,} ({pct:5.1f}%)")
        self.stdout.write(f"  {'合計':14s}: ¥{total:>15,}")

    # ============================================================
    # 診断 6: ShareDashboardView の内部値ダンプ (最重要)
    # ============================================================
    def _diag_6_share_dashboard_internals(
        self,
        member_id: int | None,
        user_id: int | None,
    ) -> None:
        """ShareDashboardView のロジックを部分的に再現し、内訳をダンプする。

        - stock_holdings / margin_stock_holdings / fund_holdings の件数と評価額
        - non_stock_value 内訳
        - monthly_chart[0] と [-1] の value
        """
        self.stdout.write(self.style.NOTICE("\n[診断 6] MTD 内部値ダンプ"))

        # 対象アカウントの絞り込み
        account_qs = PortfolioAccount.objects.filter(is_active=True)
        if user_id is not None:
            account_qs = account_qs.filter(family_member__user_id=user_id)
        if member_id is not None:
            account_qs = account_qs.filter(family_member_id=member_id)
        accounts = list(account_qs)

        if not accounts:
            self.stdout.write("  対象アカウントなし")
            return

        from decimal import Decimal

        stock_count = 0
        stock_value_sum = Decimal(0)
        margin_count = 0
        margin_value_sum = Decimal(0)
        fund_with_proxy_count = 0
        fund_with_proxy_value_sum = Decimal(0)
        fund_orphan_count = 0
        fund_orphan_value_sum = Decimal(0)
        other_value_sum = Decimal(0)
        non_stock_total = Decimal(0)
        grand_total = Decimal(0)

        for acc in accounts:
            latest = AccountSnapshot.objects.filter(account_id=acc.id).order_by("-snapshot_date").first()
            if latest is None:
                continue
            grand_total += latest.total_value_jpy
            is_margin = acc.trading_type == "margin"

            if is_margin:
                cost = latest.total_cost_jpy or Decimal(0)
                effective = latest.total_value_jpy - cost
                margin_value_sum_local = Decimal(0)
                for h in latest.holdings.all():
                    if h.stock_id is not None and h.quantity and h.quantity > 0:
                        margin_count += 1
                        h_cost = h.cost_jpy or Decimal(0)
                        margin_value_sum += h.value_jpy - h_cost
                        margin_value_sum_local += h.value_jpy - h_cost
                non_stock_total += effective - margin_value_sum_local
            else:
                effective = latest.total_value_jpy
                stock_value_in_account = Decimal(0)
                for h in latest.holdings.all():
                    if h.stock_id is not None and h.quantity and h.quantity > 0:
                        stock_count += 1
                        stock_value_sum += h.value_jpy
                        stock_value_in_account += h.value_jpy
                    elif h.proxy_stock_id is not None:
                        fund_with_proxy_count += 1
                        fund_with_proxy_value_sum += h.value_jpy
                        stock_value_in_account += h.value_jpy
                    elif h.asset_type == "fund":
                        # ★ ここが Step 2 で対応すべき取りこぼし
                        fund_orphan_count += 1
                        fund_orphan_value_sum += h.value_jpy
                non_stock_total += effective - stock_value_in_account

            # 明細なし口座 (insurance/cash 等の monolithic スナップショット)
            if latest.holdings.count() == 0:
                other_value_sum += latest.total_value_jpy

        self.stdout.write(f"  対象口座数            : {len(accounts)}")
        self.stdout.write(f"  全口座スナップショット合計: ¥{int(grand_total):,}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("  振り分け内訳 (MTD 計算経路):"))
        self.stdout.write(f"    ① stock_holdings        : {stock_count:>4} 件, ¥{int(stock_value_sum):>15,}")
        self.stdout.write(f"    ② margin_stock_holdings : {margin_count:>4} 件, ¥{int(margin_value_sum):>15,} (損益額)")
        self.stdout.write(
            f"    ③ fund_holdings (proxy済) : {fund_with_proxy_count:>4} 件, ¥{int(fund_with_proxy_value_sum):>15,}"
        )
        self.stdout.write(
            f"    ④ fund_orphan (取りこぼし): {fund_orphan_count:>4} 件, ¥{int(fund_orphan_value_sum):>15,}"
        )
        self.stdout.write(f"    ⑤ non_stock_value       : ¥{int(non_stock_total):>15,}")
        self.stdout.write("")

        # monthly_chart の chart[0].value 推定
        stock_value_sum_at_today = stock_value_sum + margin_value_sum + fund_with_proxy_value_sum
        chart_value_estimate = non_stock_total + stock_value_sum_at_today
        self.stdout.write(self.style.NOTICE("  monthly_chart 推定値:"))
        self.stdout.write(f"    chart[*].value 推定 (non_stock + stock_total): ¥{int(chart_value_estimate):,}")
        self.stdout.write(f"    grand_total との差    : ¥{int(grand_total - chart_value_estimate):,}")

        if fund_orphan_count > 0:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    f"  ⚠️ 取りこぼし投信 {fund_orphan_count} 件 / ¥{int(fund_orphan_value_sum):,} が "
                    "MTD 計算から消失しています。Step 2 (CSV 取込時 proxy 自動紐付け + views.py "
                    "の取りこぼし対応) で解消できます。"
                )
            )
