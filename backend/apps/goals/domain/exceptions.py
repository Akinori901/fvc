"""目標管理ドメイン例外。"""


class GoalNotFoundError(Exception):
    """指定された目標が存在しない"""


class DuplicateScopeError(Exception):
    """同じスコープの目標が既に存在する"""


class InvalidGoalError(Exception):
    """目標の値が不正（金額0以下、日付過去等）"""
