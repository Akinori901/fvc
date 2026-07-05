"""merge_portfolio_accounts 管理コマンドの統合テスト (DB 経由)。"""

from __future__ import annotations

import datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.portfolios.models import AccountSnapshot, FamilyMember, PortfolioAccount


@pytest.mark.django_db
class TestMergePortfolioAccountsCommand:
    def _setup_accounts(self) -> tuple[PortfolioAccount, PortfolioAccount, FamilyMember]:
        user = get_user_model().objects.create_user(username="merge_test", email="merge@example.com", password="x")
        member = FamilyMember.objects.create(user=user, name="章了", role="self")
        src = PortfolioAccount.objects.create(
            family_member=member,
            institution="SBI証券",
            institution_type="securities_jp",
            asset_class="fund",
            trading_type="spot",
            nickname="SBI特定投資信託",
            currency="JPY",
        )
        dst = PortfolioAccount.objects.create(
            family_member=member,
            institution="SBI証券",
            institution_type="securities_jp",
            asset_class="fund",
            trading_type="spot",
            nickname="特定預り",
            currency="JPY",
        )
        return src, dst, member

    def test_dry_run_does_not_modify(self) -> None:
        src, dst, _ = self._setup_accounts()
        AccountSnapshot.objects.create(
            account=src, snapshot_date=datetime.date(2026, 3, 31), total_value_jpy=Decimal("100000")
        )
        AccountSnapshot.objects.create(
            account=src, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("110000")
        )

        out = StringIO()
        call_command("merge_portfolio_accounts", "--from-id", src.id, "--to-id", dst.id, "--dry-run", stdout=out)

        assert "DRY RUN" in out.getvalue()
        # データは変化なし
        assert AccountSnapshot.objects.filter(account_id=src.id).count() == 2
        assert AccountSnapshot.objects.filter(account_id=dst.id).count() == 0
        assert PortfolioAccount.objects.filter(pk=src.id).exists()

    def test_real_run_moves_snapshots_and_deletes_src(self) -> None:
        src, dst, _ = self._setup_accounts()
        AccountSnapshot.objects.create(
            account=src, snapshot_date=datetime.date(2026, 3, 31), total_value_jpy=Decimal("100000")
        )
        AccountSnapshot.objects.create(
            account=src, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("110000")
        )
        AccountSnapshot.objects.create(
            account=dst, snapshot_date=datetime.date(2026, 5, 27), total_value_jpy=Decimal("923118")
        )

        out = StringIO()
        call_command("merge_portfolio_accounts", "--from-id", src.id, "--to-id", dst.id, stdout=out)

        assert "完了: 2 件" in out.getvalue()
        assert AccountSnapshot.objects.filter(account_id=src.id).count() == 0
        assert AccountSnapshot.objects.filter(account_id=dst.id).count() == 3  # 旧 2 + 新 1
        assert not PortfolioAccount.objects.filter(pk=src.id).exists()
        assert PortfolioAccount.objects.filter(pk=dst.id).exists()

    def test_aborts_on_date_conflict(self) -> None:
        src, dst, _ = self._setup_accounts()
        AccountSnapshot.objects.create(
            account=src, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("100000")
        )
        AccountSnapshot.objects.create(
            account=dst, snapshot_date=datetime.date(2026, 4, 30), total_value_jpy=Decimal("200000")
        )

        out = StringIO()
        err = StringIO()
        call_command("merge_portfolio_accounts", "--from-id", src.id, "--to-id", dst.id, stdout=out, stderr=err)
        # 中止 → src は残ったまま
        assert AccountSnapshot.objects.filter(account_id=src.id).count() == 1
        assert PortfolioAccount.objects.filter(pk=src.id).exists()
        assert "衝突" in out.getvalue()

    def test_aborts_on_different_family_member(self) -> None:
        src, _dst, _member = self._setup_accounts()
        user2 = get_user_model().objects.create_user(username="other_user", email="o@x.com", password="x")
        member2 = FamilyMember.objects.create(user=user2, name="他人", role="other")
        other_dst = PortfolioAccount.objects.create(
            family_member=member2,
            institution="SBI証券",
            institution_type="securities_jp",
            asset_class="fund",
            trading_type="spot",
            nickname="特定預り",
            currency="JPY",
        )

        err = StringIO()
        call_command(
            "merge_portfolio_accounts",
            "--from-id",
            src.id,
            "--to-id",
            other_dst.id,
            stdout=StringIO(),
            stderr=err,
        )
        assert "family_member_id" in err.getvalue()
        # 両方残っている
        assert PortfolioAccount.objects.filter(pk=src.id).exists()
        assert PortfolioAccount.objects.filter(pk=other_dst.id).exists()

    def test_aborts_when_account_not_found(self) -> None:
        err = StringIO()
        call_command(
            "merge_portfolio_accounts",
            "--from-id",
            99999,
            "--to-id",
            99998,
            stdout=StringIO(),
            stderr=err,
        )
        assert "見つかりません" in err.getvalue()

    def test_rejects_same_id(self) -> None:
        src, _, _ = self._setup_accounts()
        err = StringIO()
        call_command(
            "merge_portfolio_accounts",
            "--from-id",
            src.id,
            "--to-id",
            src.id,
            stdout=StringIO(),
            stderr=err,
        )
        assert "同じ" in err.getvalue()
        # 残っている
        assert PortfolioAccount.objects.filter(pk=src.id).exists()

    def test_handles_src_with_no_snapshots(self) -> None:
        """snapshot が無い空の src 口座でも src を削除して終了する。"""
        src, dst, _ = self._setup_accounts()
        # src に snapshot を作らない
        out = StringIO()
        call_command("merge_portfolio_accounts", "--from-id", src.id, "--to-id", dst.id, stdout=out)
        # src は削除される
        assert not PortfolioAccount.objects.filter(pk=src.id).exists()
        assert PortfolioAccount.objects.filter(pk=dst.id).exists()
