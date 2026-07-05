"""FXデータ同期ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..services.fx_data_sync_service import FxDataSyncService


class SyncFxDataUseCase:
    """sync_fx_data コマンドのビジネスロジック"""

    def __init__(self, sync_service: FxDataSyncService) -> None:
        self._sync_service = sync_service

    def execute(self, *, full: bool = False) -> dict[str, Any]:
        return self._sync_service.sync_all(full=full)
