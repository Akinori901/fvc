"""ニュース機能ドメイン例外。"""


class NewsSourceError(Exception):
    """ニュースソース（外部API/RSS）からの取得エラー"""


class NewsAnalysisError(Exception):
    """ニュース AI 分析エラー（Phase 2 で使用）"""
