"""投資信託 → プロキシETF の紐付け解決サービス。

投資信託は基準価額を日次取得していないため、値動きの近い指数ETF（プロキシETF）の
変動率で日次評価を近似する。本モジュールは「投信の銘柄名からプロキシETFコードを解決する」
純粋ロジックを提供し、CSV取込時（自動紐付け）と `link_fund_proxies` コマンド（一括紐付け）の
両方から共通利用する。

解決ルール: asset_name の部分一致。FUND_PROXY_MAP を先頭から走査し、最初にマッチした
キーワードのプロキシETFコードを返す（＝リスト順が優先度）。
"""

from __future__ import annotations

# asset_name の部分一致 → プロキシETFコード（先頭から優先マッチ）
# 順序が優先度を持つため、より具体的なキーワードを上に置く。
FUND_PROXY_MAP: list[tuple[str, str]] = [
    ("S&P500", "1557"),
    ("Ｓ＆Ｐ５００", "1557"),
    ("米国株式", "1557"),
    ("米国成長株", "1557"),
    ("全米株式", "VTI"),
    ("VTI", "VTI"),
    ("オールカントリー", "ACWI"),
    ("オール・カントリー", "ACWI"),
    ("全世界株式", "ACWI"),
    ("FANG+", "QQQ"),
    ("ＦＡＮＧ", "QQQ"),
    ("NASDAQ", "1545"),
    ("ＮＡＳＤＡＱ", "1545"),
    ("日経225", "1321"),
    ("日経平均", "1321"),
    ("日本株", "1321"),
    ("国内株", "1321"),
    ("TOPIX", "1321"),
    ("中小型", "1321"),
    ("先進国株式", "1550"),
    ("インド", "1678"),
    ("ゴールド", "GLD"),
    ("Gold", "GLD"),
    ("おおぶね", "1557"),
]


def resolve_proxy_code(asset_name: str) -> str | None:
    """投信の銘柄名からプロキシETFコードを解決する。

    FUND_PROXY_MAP を先頭から走査し、asset_name に含まれる最初のキーワードの
    プロキシETFコードを返す。マッチしなければ None。
    """
    for keyword, code in FUND_PROXY_MAP:
        if keyword in asset_name:
            return code
    return None
