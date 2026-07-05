"""FX分析リポジトリインターフェース。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from .entities import FxRateEntity, InterestRateEntity, MacroIndicatorEntity


class FxRateRepository(ABC):
    """為替レートリポジトリ"""

    @abstractmethod
    def find_all(self, pair: str = "USDJPY", limit: int | None = None) -> list[FxRateEntity]: ...

    @abstractmethod
    def find_latest(self, pair: str = "USDJPY") -> FxRateEntity | None: ...

    @abstractmethod
    def find_latest_date(self, pair: str = "USDJPY") -> date | None: ...

    @abstractmethod
    def bulk_save(self, entities: list[FxRateEntity]) -> int: ...


class InterestRateRepository(ABC):
    """金利リポジトリ"""

    @abstractmethod
    def find_all(self, country: str, rate_type: str = "10Y") -> list[InterestRateEntity]: ...

    @abstractmethod
    def find_latest(self, country: str, rate_type: str = "10Y") -> InterestRateEntity | None: ...

    @abstractmethod
    def find_latest_date(self, country: str, rate_type: str = "10Y") -> date | None: ...

    @abstractmethod
    def bulk_save(self, entities: list[InterestRateEntity]) -> int: ...


class MacroIndicatorRepository(ABC):
    """マクロ指標リポジトリ"""

    @abstractmethod
    def find_latest(self, indicator_type: str) -> MacroIndicatorEntity | None: ...

    @abstractmethod
    def save(self, entity: MacroIndicatorEntity) -> MacroIndicatorEntity: ...
