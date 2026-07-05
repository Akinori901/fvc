"""仮想売買リポジトリABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import PaperPositionEntity, PaperTradeEntity


class PaperTradeRepository(ABC):
    """売買記録リポジトリインターフェース"""

    @abstractmethod
    def save(self, entity: PaperTradeEntity) -> PaperTradeEntity: ...

    @abstractmethod
    def find_by_user(self, user_id: int, stock_id: int | None = None) -> list[PaperTradeEntity]: ...

    @abstractmethod
    def delete_all_by_user(self, user_id: int) -> int: ...


class PaperPositionRepository(ABC):
    """ポジション集計リポジトリインターフェース"""

    @abstractmethod
    def find_by_user_and_stock(self, user_id: int, stock_id: int) -> PaperPositionEntity | None: ...

    @abstractmethod
    def find_all_by_user(self, user_id: int) -> list[PaperPositionEntity]: ...

    @abstractmethod
    def save(self, entity: PaperPositionEntity) -> PaperPositionEntity: ...

    @abstractmethod
    def delete_all_by_user(self, user_id: int) -> int: ...
