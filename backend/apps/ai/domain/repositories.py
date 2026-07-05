"""AI機能リポジトリABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .entities import AiAnalysisLogEntity, AiConfigEntity, AiDecisionEntity


class AiConfigRepository(ABC):
    """ユーザーAI設定リポジトリインターフェース"""

    @abstractmethod
    def find_by_user_id(self, user_id: int) -> AiConfigEntity | None: ...

    @abstractmethod
    def save(self, entity: AiConfigEntity) -> AiConfigEntity: ...


class AiAnalysisLogRepository(ABC):
    """AI分析ログリポジトリインターフェース"""

    @abstractmethod
    def save(self, entity: AiAnalysisLogEntity) -> AiAnalysisLogEntity: ...

    @abstractmethod
    def count_since(self, user_id: int, since: datetime) -> int:
        """レート制限チェック: 指定日時以降の成功リクエスト数を返す"""
        ...


class AiDecisionRepository(ABC):
    """AI 判断履歴リポジトリインターフェース"""

    @abstractmethod
    def save(self, entity: AiDecisionEntity) -> AiDecisionEntity: ...

    @abstractmethod
    def find_by_user(self, user_id: int, limit: int = 50) -> list[AiDecisionEntity]:
        """ユーザーの判断履歴を decided_at 降順で返す"""
