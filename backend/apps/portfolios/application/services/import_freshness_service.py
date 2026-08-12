"""口座スナップショットの「取込漏れ」を検知するサービス。

`assetbalance` 系CSVに含まれない口座（信用・iDeCo・ジュニアNISA等）は専用CSVを
取り込まないと更新されず、明細が欠落したり更新が止まったりする（2026-07-07 調査）。
本サービスは各口座の最新スナップショットを見て、以下の警告を純粋ロジックで判定する。

- ``no_detail``: 本来明細を持つべき株式・投信系口座なのに holdings が0件（明細欠落の疑い）
- ``stale``: 最新スナップショットが閾値日数以上前（更新が止まっている疑い）

データは一切変更しない。判定のみ。「売却して現金化した」ケースと「取込漏れ」は
データから区別できないため、自動でデータを補完せず、人間が確認するための警告に留める。
"""

from __future__ import annotations

import datetime

# 本来「明細（holdings）」を持つべき asset_class。
# これ以外（cash/insurance/mutual_aid/loan/real_estate/bond/other）は
# 口座合計だけの monolithic 計上が正常なので no_detail 判定の対象外とする。
DETAIL_EXPECTED_ASSET_CLASSES: frozenset[str] = frozenset({"jp_stock", "us_stock", "etf", "fund"})

# stale 判定のデフォルト閾値（日）。最新スナップショットがこれ以上前なら警告。
DEFAULT_STALE_DAYS = 14


def detect_account_warnings(
    asset_class: str,
    latest_snapshot_date: str | None,
    holdings_count: int,
    total_value: float,
    as_of_date: datetime.date,
    stale_days: int = DEFAULT_STALE_DAYS,
) -> list[str]:
    """1口座ぶんの取込漏れ警告を判定して返す。

    Args:
        asset_class: 口座の資産クラス
        latest_snapshot_date: 最新スナップショット日 (ISO文字列, なければ None)
        holdings_count: 最新スナップショットの明細件数
        total_value: 最新スナップショットの総額（>0 のときのみ no_detail を疑う）
        as_of_date: 判定基準日（通常 today）
        stale_days: stale 判定の閾値日数

    Returns:
        警告コードのリスト（例: ["no_detail", "stale"]）。警告なしは空リスト。
    """
    warnings: list[str] = []

    # スナップショットが1件も無い口座は判定対象外（新規口座など）
    if latest_snapshot_date is None:
        return warnings

    # no_detail: 明細を持つべき口座なのに holdings 0件かつ総額あり
    if asset_class in DETAIL_EXPECTED_ASSET_CLASSES and holdings_count == 0 and total_value > 0:
        warnings.append("no_detail")

    # stale: 最新スナップショットが閾値以上前
    try:
        snap_date = datetime.date.fromisoformat(latest_snapshot_date)
    except ValueError:
        return warnings
    if (as_of_date - snap_date).days >= stale_days:
        warnings.append("stale")

    return warnings
