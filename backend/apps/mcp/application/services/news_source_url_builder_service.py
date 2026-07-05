"""信頼できるニュースソースの検索 URL を生成する純粋関数サービス。

実際の記事フェッチは行わない。Claude / ChatGPT が WebFetch で
返却された URL を読みに行く前提。
"""

from __future__ import annotations

from urllib.parse import quote


class NewsSourceUrlBuilderService:
    """銘柄名・キーワードから信頼ソースの検索 URL リストを生成。"""

    def build(self, *, stock_name: str, query: str | None = None) -> list[dict[str, str]]:
        """検索 URL のリストを返す。

        Returns:
            [{"name": ..., "url": ..., "tier": "primary"|"secondary"}, ...]
        """
        q = (query or stock_name).strip()
        if not q:
            return []
        encoded = quote(q)

        # 一次情報源（公式開示・公式リリース）
        primary: list[dict[str, str]] = [
            {
                "name": "適時開示情報閲覧サービス (TDnet)",
                "url": "https://www.release.tdnet.info/inbs/I_main_00.html",
                "tier": "primary",
                "note": "TDnet トップから銘柄コードで検索（直リンク不可）",
            },
            {
                "name": "EDINET",
                "url": f"https://disclosure2.edinet-fsa.go.jp/WEEK0010.aspx?SESSIONKEY=&filterPubYear=&filterPubMonth=&filterPubDay=&companyName={encoded}",
                "tier": "primary",
            },
        ]

        # 報道機関
        secondary: list[dict[str, str]] = [
            {
                "name": "日本経済新聞",
                "url": f"https://www.nikkei.com/search?keyword={encoded}",
                "tier": "secondary",
            },
            {
                "name": "Reuters Japan",
                "url": f"https://jp.reuters.com/site-search/?query={encoded}",
                "tier": "secondary",
            },
            {
                "name": "Bloomberg",
                "url": f"https://www.bloomberg.co.jp/search?query={encoded}",
                "tier": "secondary",
            },
            {
                "name": "Yahoo!ファイナンス（時系列＋ニュース）",
                "url": f"https://finance.yahoo.co.jp/search?query={encoded}",
                "tier": "secondary",
            },
        ]

        return primary + secondary
