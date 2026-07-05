from abc import ABC, abstractmethod

from .entities import ValuationResult


class ValuationRepository(ABC):
    """適正価格算出結果リポジトリインターフェース"""

    @abstractmethod
    def save(self, entity: ValuationResult) -> ValuationResult: ...

    @abstractmethod
    def find_by_stock_id(self, stock_id: int, user_id: int) -> list[ValuationResult]: ...

    @abstractmethod
    def find_by_id(self, valuation_id: int, user_id: int) -> ValuationResult | None: ...

    @abstractmethod
    def list_all(self, user_id: int, limit: int = 50) -> list[ValuationResult]: ...
