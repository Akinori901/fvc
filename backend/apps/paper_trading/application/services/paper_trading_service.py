"""仮想売買サービス。売買実行とポジション更新を担当する。"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from apps.paper_trading.domain.entities import PaperPositionEntity, PaperTradeEntity
from apps.paper_trading.domain.exceptions import (
    InsufficientPositionError,
    InvalidTradeQuantityError,
)

if TYPE_CHECKING:
    from apps.paper_trading.domain.repositories import (
        PaperPositionRepository,
        PaperTradeRepository,
    )

_TRADE_UNIT = 100


class PaperTradingService:
    """売買実行 + ポジション更新ロジック。"""

    def __init__(
        self,
        trade_repo: PaperTradeRepository,
        position_repo: PaperPositionRepository,
    ) -> None:
        self._trade_repo = trade_repo
        self._position_repo = position_repo

    def execute_buy(
        self,
        user_id: int,
        stock_id: int,
        quantity: int,
        price: Decimal,
        memo: str = "",
    ) -> tuple[PaperTradeEntity, PaperPositionEntity]:
        self._validate_quantity(quantity)

        total_amount = price * quantity
        now = datetime.now(tz=UTC)

        # ポジション upsert
        position = self._position_repo.find_by_user_and_stock(user_id, stock_id)
        if position is None:
            position = PaperPositionEntity(
                user_id=user_id,
                stock_id=stock_id,
                quantity=quantity,
                total_cost=total_amount,
                avg_cost_price=price,
                realized_profit_total=Decimal("0"),
            )
        else:
            new_total_cost = position.total_cost + total_amount
            new_quantity = position.quantity + quantity
            position.avg_cost_price = (new_total_cost / new_quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            position.quantity = new_quantity
            position.total_cost = new_total_cost

        position = self._position_repo.save(position)

        # 売買記録
        trade = self._trade_repo.save(
            PaperTradeEntity(
                user_id=user_id,
                stock_id=stock_id,
                trade_type="buy",
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                memo=memo,
                traded_at=now,
            )
        )

        return trade, position

    def execute_sell(
        self,
        user_id: int,
        stock_id: int,
        quantity: int,
        price: Decimal,
        memo: str = "",
    ) -> tuple[PaperTradeEntity, PaperPositionEntity]:
        self._validate_quantity(quantity)

        position = self._position_repo.find_by_user_and_stock(user_id, stock_id)
        if position is None or position.quantity == 0:
            raise InsufficientPositionError("この銘柄のポジションがありません。")
        if position.quantity < quantity:
            msg = f"保有数が不足しています。現在の保有数: {position.quantity}株"
            raise InsufficientPositionError(msg)

        total_amount = price * quantity
        realized_profit = (price - position.avg_cost_price) * quantity
        now = datetime.now(tz=UTC)

        # 売買記録（avg_cost スナップショット付き）
        trade = self._trade_repo.save(
            PaperTradeEntity(
                user_id=user_id,
                stock_id=stock_id,
                trade_type="sell",
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                realized_profit=realized_profit,
                avg_cost_at_trade=position.avg_cost_price,
                memo=memo,
                traded_at=now,
            )
        )

        # ポジション更新
        new_quantity = position.quantity - quantity
        position.quantity = new_quantity
        position.total_cost = position.avg_cost_price * new_quantity
        position.realized_profit_total += realized_profit
        position = self._position_repo.save(position)

        return trade, position

    def _validate_quantity(self, quantity: int) -> None:
        if quantity <= 0 or quantity % _TRADE_UNIT != 0:
            raise InvalidTradeQuantityError("数量は100株単位で入力してください。")
