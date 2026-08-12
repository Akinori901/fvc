"""fund_proxy_service.resolve_proxy_code の単体テスト（DB非依存の純粋関数）。"""

from __future__ import annotations

import pytest

from apps.portfolios.application.services.fund_proxy_service import (
    FUND_PROXY_MAP,
    resolve_proxy_code,
)


class TestResolveProxyCode:
    @pytest.mark.parametrize(
        ("asset_name", "expected"),
        [
            ("eMAXIS Slim 米国株式(S&P500)", "1557"),
            ("楽天・全米株式インデックス・ファンド(楽天・VTI)", "VTI"),
            ("eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)", "ACWI"),
            ("iFreeNEXT FANG+インデックス", "QQQ"),
            ("ニッセイNASDAQ100インデックスファンド", "1545"),
            ("eMAXIS Slim 国内株式(日経平均)", "1321"),
            ("eMAXIS Slim 国内株式(TOPIX)", "1321"),
            ("iTrust インド株式", "1678"),
            ("先進国株式インデックス", "1550"),
            ("ゴールド・ファンド", "GLD"),
        ],
    )
    def test_known_funds_resolve(self, asset_name: str, expected: str) -> None:
        assert resolve_proxy_code(asset_name) == expected

    def test_unmatched_returns_none(self) -> None:
        # 外国REIT はマッピングにキーワードがないため None
        assert resolve_proxy_code("三井住友・DC外国リートインデックスファンド") is None
        assert resolve_proxy_code("") is None

    def test_priority_is_list_order(self) -> None:
        # FUND_PROXY_MAP はリスト順が優先度。先頭のキーワードが先に評価される。
        # "米国株式" (1557) は "全米株式" (VTI) より前に定義されているが、
        # "全米株式" を含む名前は "米国株式" を含まないので VTI に解決される。
        assert resolve_proxy_code("全米株式インデックス") == "VTI"
        # "S&P500" は "米国株式" より前 → S&P500 名は 1557
        assert resolve_proxy_code("米国株式S&P500") == "1557"

    def test_map_codes_are_nonempty(self) -> None:
        # マッピングの妥当性（キーワード・コードともに非空）
        for keyword, code in FUND_PROXY_MAP:
            assert keyword
            assert code
