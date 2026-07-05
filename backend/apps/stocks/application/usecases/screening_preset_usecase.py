"""スクリーニングプリセットCRUDユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.stocks.domain.repositories import ScreeningPresetRepository
    from apps.stocks.domain.screening_preset import ScreeningPresetEntity


class ListScreeningPresetsUseCase:
    """ユーザーのプリセット一覧を取得。"""

    def __init__(self, preset_repo: ScreeningPresetRepository) -> None:
        self._repo = preset_repo

    def execute(self, user_id: int) -> list[ScreeningPresetEntity]:
        return self._repo.find_by_user_id(user_id)


class SaveScreeningPresetUseCase:
    """プリセットを作成または更新。"""

    def __init__(self, preset_repo: ScreeningPresetRepository) -> None:
        self._repo = preset_repo

    def execute(
        self,
        user_id: int,
        name: str,
        priority: int,
        filters: dict[str, Any],
        preset_id: int | None = None,
    ) -> ScreeningPresetEntity:
        from apps.stocks.domain.screening_preset import ScreeningPresetEntity

        entity = ScreeningPresetEntity(
            id=preset_id,
            user_id=user_id,
            name=name,
            priority=priority,
            filters=filters,
        )
        return self._repo.save(entity)


class DeleteScreeningPresetUseCase:
    """プリセットを削除。"""

    def __init__(self, preset_repo: ScreeningPresetRepository) -> None:
        self._repo = preset_repo

    def execute(self, preset_id: int, user_id: int) -> bool:
        return self._repo.delete(preset_id, user_id)
