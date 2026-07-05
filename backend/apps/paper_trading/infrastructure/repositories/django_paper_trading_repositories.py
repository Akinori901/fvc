"""仮想売買Djangoリポジトリ実装。"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.paper_trading.domain.entities import PaperPositionEntity, PaperTradeEntity
from apps.paper_trading.domain.repositories import (
    PaperPositionRepository,
    PaperTradeRepository,
)
from apps.paper_trading.infrastructure.models import PaperPosition, PaperTrade


class DjangoPaperTradeRepository(PaperTradeRepository):
    """売買記録リポジトリ Django実装。"""

    def save(self, entity: PaperTradeEntity) -> PaperTradeEntity:
        traded_at = entity.traded_at or datetime.now(tz=UTC)
        obj = PaperTrade.objects.create(
            user_id=entity.user_id,
            stock_id=entity.stock_id,
            trade_type=entity.trade_type,
            quantity=entity.quantity,
            price=entity.price,
            total_amount=entity.total_amount,
            realized_profit=entity.realized_profit,
            avg_cost_at_trade=entity.avg_cost_at_trade,
            memo=entity.memo,
            traded_at=traded_at,
        )
        entity.id = obj.pk
        entity.created_at = obj.created_at
        return entity

    def find_by_user(self, user_id: int, stock_id: int | None = None) -> list[PaperTradeEntity]:
        qs = PaperTrade.objects.filter(user_id=user_id).select_related("stock")
        if stock_id is not None:
            qs = qs.filter(stock_id=stock_id)
        return [self._to_entity(obj) for obj in qs]

    def delete_all_by_user(self, user_id: int) -> int:
        count, _ = PaperTrade.objects.filter(user_id=user_id).delete()
        return count

    def _to_entity(self, obj: PaperTrade) -> PaperTradeEntity:
        return PaperTradeEntity(
            id=obj.pk,
            user_id=obj.user_id,
            stock_id=obj.stock_id,
            trade_type=obj.trade_type,
            quantity=obj.quantity,
            price=obj.price,
            total_amount=obj.total_amount,
            realized_profit=obj.realized_profit,
            avg_cost_at_trade=obj.avg_cost_at_trade,
            memo=obj.memo,
            traded_at=obj.traded_at,
            created_at=obj.created_at,
        )


class DjangoPaperPositionRepository(PaperPositionRepository):
    """ポジション集計リポジトリ Django実装。"""

    def find_by_user_and_stock(self, user_id: int, stock_id: int) -> PaperPositionEntity | None:
        try:
            obj = PaperPosition.objects.get(user_id=user_id, stock_id=stock_id)
        except PaperPosition.DoesNotExist:
            return None
        return self._to_entity(obj)

    def find_all_by_user(self, user_id: int) -> list[PaperPositionEntity]:
        qs = PaperPosition.objects.filter(user_id=user_id, quantity__gt=0).select_related("stock")
        return [self._to_entity(obj) for obj in qs]

    def save(self, entity: PaperPositionEntity) -> PaperPositionEntity:
        if entity.id:
            PaperPosition.objects.filter(pk=entity.id).update(
                quantity=entity.quantity,
                total_cost=entity.total_cost,
                avg_cost_price=entity.avg_cost_price,
                realized_profit_total=entity.realized_profit_total,
            )
        else:
            obj = PaperPosition.objects.create(
                user_id=entity.user_id,
                stock_id=entity.stock_id,
                quantity=entity.quantity,
                total_cost=entity.total_cost,
                avg_cost_price=entity.avg_cost_price,
                realized_profit_total=entity.realized_profit_total,
            )
            entity.id = obj.pk
        return entity

    def delete_all_by_user(self, user_id: int) -> int:
        count, _ = PaperPosition.objects.filter(user_id=user_id).delete()
        return count

    def _to_entity(self, obj: PaperPosition) -> PaperPositionEntity:
        return PaperPositionEntity(
            id=obj.pk,
            user_id=obj.user_id,
            stock_id=obj.stock_id,
            quantity=obj.quantity,
            total_cost=obj.total_cost,
            avg_cost_price=obj.avg_cost_price,
            realized_profit_total=obj.realized_profit_total,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
