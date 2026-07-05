"""業界指標リポジトリABC。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import IndustryMetricsEntity


class IndustryMetricsRepository(ABC):
    @abstractmethod
    def find_by_sector(self, sector: str) -> IndustryMetricsEntity | None: ...

    @abstractmethod
    def upsert(self, entity: IndustryMetricsEntity) -> IndustryMetricsEntity: ...

    @abstractmethod
    def list_all(self) -> list[IndustryMetricsEntity]: ...
