"""仮想売買リセットユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

if TYPE_CHECKING:
    from apps.paper_trading.domain.repositories import (
        PaperPositionRepository,
        PaperTradeRepository,
    )


class ResetPaperTradingUseCase:
    def __init__(
        self,
        trade_repo: PaperTradeRepository,
        position_repo: PaperPositionRepository,
    ) -> None:
        self._trade_repo = trade_repo
        self._position_repo = position_repo

    @transaction.atomic
    def execute(self, user_id: int) -> tuple[int, int]:
        """全売買データを削除し、(deleted_trades, deleted_positions) を返す。"""
        deleted_trades = self._trade_repo.delete_all_by_user(user_id)
        deleted_positions = self._position_repo.delete_all_by_user(user_id)
        return deleted_trades, deleted_positions
