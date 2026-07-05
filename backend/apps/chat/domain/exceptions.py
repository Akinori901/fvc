"""チャット機能のドメイン例外。"""

from __future__ import annotations


class ChatError(Exception):
    """チャット機能のベース例外。"""


class ChatConfigMissingError(ChatError):
    """BYOK 設定が未登録または無効。

    UI 側では設定画面（`/settings`）への誘導に使う。
    """

    def __init__(self, message: str = "AI設定が登録されていません。設定画面でAPIキーを登録してください。") -> None:
        super().__init__(message)


class ChatDailyLimitExceededError(ChatError):
    """1日あたりの安全弁（200 質問）に到達した。"""

    def __init__(self, limit: int, current: int) -> None:
        self.limit = limit
        self.current = current
        super().__init__(
            f"本日の上限（{limit}質問）に到達しました（現在: {current}件）。明日のJST 0時にリセットされます。"
        )


class ChatSessionNotFoundError(ChatError):
    """指定されたセッションが存在しない、または当該ユーザーのものではない。"""


class ChatToolInvocationError(ChatError):
    """Function Calling 中のツール実行で予期せぬエラーが発生した。"""
