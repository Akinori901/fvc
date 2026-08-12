"""import_freshness_service.detect_account_warnings の単体テスト（DB非依存）。"""

from __future__ import annotations

import datetime

from apps.portfolios.application.services.import_freshness_service import (
    DEFAULT_STALE_DAYS,
    detect_account_warnings,
)

TODAY = datetime.date(2026, 7, 7)


def _recent(days_ago: int) -> str:
    return (TODAY - datetime.timedelta(days=days_ago)).isoformat()


class TestNoDetail:
    def test_fund_with_zero_holdings_and_value_is_flagged(self) -> None:
        w = detect_account_warnings("fund", _recent(0), holdings_count=0, total_value=1_000_000, as_of_date=TODAY)
        assert "no_detail" in w

    def test_jp_stock_with_zero_holdings_is_flagged(self) -> None:
        w = detect_account_warnings("jp_stock", _recent(0), holdings_count=0, total_value=500_000, as_of_date=TODAY)
        assert "no_detail" in w

    def test_fund_with_holdings_is_not_flagged(self) -> None:
        w = detect_account_warnings("fund", _recent(0), holdings_count=3, total_value=1_000_000, as_of_date=TODAY)
        assert "no_detail" not in w

    def test_zero_value_is_not_flagged(self) -> None:
        # 全部売却して残高0の口座は no_detail 扱いにしない
        w = detect_account_warnings("fund", _recent(0), holdings_count=0, total_value=0, as_of_date=TODAY)
        assert "no_detail" not in w

    def test_cash_account_is_not_flagged(self) -> None:
        # 現金は元々明細を持たない monolithic 計上なので対象外
        w = detect_account_warnings("cash", _recent(0), holdings_count=0, total_value=3_000_000, as_of_date=TODAY)
        assert "no_detail" not in w

    def test_insurance_and_mutual_aid_not_flagged(self) -> None:
        for cls in ("insurance", "mutual_aid", "loan", "real_estate", "jp_bond", "us_bond", "other"):
            w = detect_account_warnings(cls, _recent(0), holdings_count=0, total_value=5_000_000, as_of_date=TODAY)
            assert "no_detail" not in w, cls


class TestStale:
    def test_snapshot_older_than_threshold_is_stale(self) -> None:
        w = detect_account_warnings(
            "fund", _recent(DEFAULT_STALE_DAYS), holdings_count=3, total_value=1_000_000, as_of_date=TODAY
        )
        assert "stale" in w

    def test_snapshot_within_threshold_is_not_stale(self) -> None:
        w = detect_account_warnings(
            "fund", _recent(DEFAULT_STALE_DAYS - 1), holdings_count=3, total_value=1_000_000, as_of_date=TODAY
        )
        assert "stale" not in w

    def test_custom_threshold(self) -> None:
        w = detect_account_warnings(
            "jp_stock", _recent(31), holdings_count=1, total_value=1_000, as_of_date=TODAY, stale_days=30
        )
        assert "stale" in w

    def test_stale_applies_to_non_detail_classes_too(self) -> None:
        # stale は asset_class を問わず判定する（現金でも更新停止は検知）
        w = detect_account_warnings("cash", _recent(20), holdings_count=0, total_value=100_000, as_of_date=TODAY)
        assert w == ["stale"]


class TestEdgeCases:
    def test_no_snapshot_returns_empty(self) -> None:
        w = detect_account_warnings("fund", None, holdings_count=0, total_value=0, as_of_date=TODAY)
        assert w == []

    def test_both_warnings_can_coexist(self) -> None:
        w = detect_account_warnings("fund", _recent(30), holdings_count=0, total_value=1_000_000, as_of_date=TODAY)
        assert set(w) == {"no_detail", "stale"}

    def test_invalid_date_string_does_not_crash(self) -> None:
        w = detect_account_warnings("fund", "not-a-date", holdings_count=0, total_value=1_000_000, as_of_date=TODAY)
        # no_detail は判定できるが stale は日付パース失敗で付かない
        assert w == ["no_detail"]
