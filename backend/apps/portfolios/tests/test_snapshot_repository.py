"""DjangoAccountSnapshotRepository の単体テスト。

特に find_each_account_latest_before (Step 1.6 で追加) の動作を検証する。
MTD 計算の baseline 取得に使われる重要メソッドのため、各種ケースを網羅する。
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.portfolios.infrastructure.repositories import DjangoAccountSnapshotRepository
from apps.portfolios.models import AccountSnapshot, FamilyMember, PortfolioAccount


@pytest.mark.django_db
class TestFindEachAccountLatestBefore:
    """find_each_account_latest_before の境界ケースを網羅。"""

    def _setup_user_with_accounts(self) -> tuple[int, PortfolioAccount, PortfolioAccount]:
        user = get_user_model().objects.create_user(username="snap_test", email="snap@example.com", password="x")
        member = FamilyMember.objects.create(user=user, name="本人", role="self")
        acc_a = PortfolioAccount.objects.create(
            family_member=member,
            institution="A証券",
            institution_type="securities_jp",
            asset_class="fund",
            trading_type="spot",
            nickname="特定",
            currency="JPY",
        )
        acc_b = PortfolioAccount.objects.create(
            family_member=member,
            institution="B証券",
            institution_type="securities_jp",
            asset_class="jp_stock",
            trading_type="spot",
            nickname="特定",
            currency="JPY",
        )
        return user.pk, acc_a, acc_b

    def test_returns_latest_snapshot_before_each_account(self) -> None:
        """口座毎に、as_of_date 以前で最新のスナップショットを 1 件返す。"""
        user_id, acc_a, acc_b = self._setup_user_with_accounts()

        # acc_a: 3/31, 4/15, 4/30, 5/15 (5/15 は対象外)
        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 3, 31), total_value_jpy=Decimal("100000")
        )
        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 15), total_value_jpy=Decimal("110000")
        )
        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("120000")
        )
        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 5, 15), total_value_jpy=Decimal("130000")
        )
        # acc_b: 4/10, 4/25
        AccountSnapshot.objects.create(
            account=acc_b, snapshot_date=datetime.date(2026, 4, 10), total_value_jpy=Decimal("200000")
        )
        AccountSnapshot.objects.create(
            account=acc_b, snapshot_date=datetime.date(2026, 4, 25), total_value_jpy=Decimal("210000")
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        by_account = {s.account_id: s for s in result}
        assert len(result) == 2
        assert by_account[acc_a.pk].snapshot_date == "2026-04-30"
        assert by_account[acc_a.pk].total_value_jpy == Decimal("120000")
        assert by_account[acc_b.pk].snapshot_date == "2026-04-25"
        assert by_account[acc_b.pk].total_value_jpy == Decimal("210000")

    def test_excludes_account_with_no_snapshot_before_date(self) -> None:
        """as_of_date 以前にスナップショットが無い口座は結果に含まれない。"""
        user_id, acc_a, acc_b = self._setup_user_with_accounts()

        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )
        # acc_b は 5/15 だけ
        AccountSnapshot.objects.create(
            account=acc_b, snapshot_date=datetime.date(2026, 5, 15), total_value_jpy=Decimal("200000")
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        assert len(result) == 1
        assert result[0].account_id == acc_a.pk

    def test_includes_snapshot_exactly_on_date(self) -> None:
        """as_of_date ぴったりのスナップショットは結果に含まれる (lte の確認)。"""
        user_id, acc_a, _ = self._setup_user_with_accounts()

        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        assert len(result) == 1
        assert result[0].snapshot_date == "2026-04-30"

    def test_does_not_include_other_users_snapshots(self) -> None:
        """別ユーザーのスナップショットは混入しない。"""
        user_id, acc_a, _ = self._setup_user_with_accounts()
        AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )

        # 別ユーザー + 口座 + スナップショット
        other_user = get_user_model().objects.create_user(username="other", email="other@example.com", password="x")
        other_member = FamilyMember.objects.create(user=other_user, name="他人", role="self")
        other_acc = PortfolioAccount.objects.create(
            family_member=other_member,
            institution="X",
            institution_type="securities_jp",
            asset_class="fund",
            trading_type="spot",
            currency="JPY",
        )
        AccountSnapshot.objects.create(
            account=other_acc, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("999999")
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        assert len(result) == 1
        assert result[0].account_id == acc_a.pk

    def test_holdings_are_empty_by_default_for_lightweight_query(self) -> None:
        """with_holdings=False (デフォルト) では holdings を読み込まない (パフォーマンス重視)。"""
        from apps.portfolios.models import AccountHolding

        user_id, acc_a, _ = self._setup_user_with_accounts()
        snap = AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )
        AccountHolding.objects.create(
            snapshot=snap,
            asset_name="dummy",
            asset_type="fund",
            value_jpy=Decimal("100000"),
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        assert len(result) == 1
        assert result[0].holdings == []

    def test_holdings_are_loaded_when_with_holdings_true(self) -> None:
        """with_holdings=True なら holdings も読み込む (DynamicValuationService 用)。"""
        from apps.portfolios.models import AccountHolding

        user_id, acc_a, _ = self._setup_user_with_accounts()
        snap = AccountSnapshot.objects.create(
            account=acc_a, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )
        AccountHolding.objects.create(
            snapshot=snap,
            asset_name="ファンドA",
            asset_type="fund",
            value_jpy=Decimal("100000"),
        )

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30", with_holdings=True)

        assert len(result) == 1
        assert len(result[0].holdings) == 1
        assert result[0].holdings[0].asset_name == "ファンドA"

    def test_returns_empty_when_no_snapshots(self) -> None:
        """スナップショット 0 件のとき空リストを返す (例外を投げない)。"""
        user_id, _, _ = self._setup_user_with_accounts()

        repo = DjangoAccountSnapshotRepository()
        result = repo.find_each_account_latest_before(user_id, "2026-04-30")

        assert result == []
