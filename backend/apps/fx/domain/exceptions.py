"""FX分析ドメイン例外。"""


class FxDataNotFoundError(Exception):
    """FXデータが不足（同期未実行）"""


class FredApiError(Exception):
    """FRED API呼び出しエラー"""
