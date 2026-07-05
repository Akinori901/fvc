"""スクリーニングプリセットエンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScreeningPresetEntity:
    """ユーザー保存のスクリーニングフィルタープリセット"""

    user_id: int
    name: str
    priority: int = 0  # 小さいほど優先
    filters: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
