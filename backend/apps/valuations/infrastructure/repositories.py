from ..domain.entities import ValuationResult
from ..domain.repositories import ValuationRepository
from ..models import Valuation


class DjangoValuationRepository(ValuationRepository):
    """Django ORM による適正価格算出結果リポジトリ実装"""

    def _to_entity(self, obj: Valuation) -> ValuationResult:
        return ValuationResult(
            id=obj.pk,
            stock_id=obj.stock_id,
            user_id=obj.user_id,
            growth_rate=obj.growth_rate,
            fair_pbr=obj.fair_pbr,
            fair_value=obj.fair_value,
            current_price=obj.current_price,
            discount_rate=obj.discount_rate,
            is_undervalued=obj.is_undervalued,
            roe=obj.roe,
            cost_of_capital=obj.cost_of_capital,
            bps=obj.bps,
            current_pbr=obj.current_pbr,
            implied_growth_rate=obj.implied_growth_rate,
        )

    def save(self, entity: ValuationResult) -> ValuationResult:
        obj = Valuation.objects.create(
            stock_id=entity.stock_id,
            user_id=entity.user_id,
            growth_rate=entity.growth_rate,
            fair_pbr=entity.fair_pbr,
            fair_value=entity.fair_value,
            current_price=entity.current_price,
            discount_rate=entity.discount_rate,
            is_undervalued=entity.is_undervalued,
            roe=entity.roe,
            cost_of_capital=entity.cost_of_capital,
            bps=entity.bps,
            current_pbr=entity.current_pbr,
            implied_growth_rate=entity.implied_growth_rate,
        )
        entity.id = obj.pk
        return entity

    def find_by_stock_id(self, stock_id: int, user_id: int) -> list[ValuationResult]:
        return [self._to_entity(obj) for obj in Valuation.objects.filter(stock_id=stock_id, user_id=user_id)]

    def find_by_id(self, valuation_id: int, user_id: int) -> ValuationResult | None:
        try:
            return self._to_entity(Valuation.objects.get(pk=valuation_id, user_id=user_id))
        except Valuation.DoesNotExist:
            return None

    def list_all(self, user_id: int, limit: int = 50) -> list[ValuationResult]:
        return [self._to_entity(obj) for obj in Valuation.objects.filter(user_id=user_id)[:limit]]
