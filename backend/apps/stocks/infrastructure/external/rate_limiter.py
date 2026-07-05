"""シンプルなスリープベースのレート制限ユーティリティ。"""

from __future__ import annotations

import time


class RateLimiter:
    """1秒あたりのAPI呼び出し回数を制限する。"""

    def __init__(self, calls_per_second: int = 10) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._last_call = 0.0

    def wait(self) -> None:
        """必要に応じてスリープし、レート制限を守る。"""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.monotonic()
