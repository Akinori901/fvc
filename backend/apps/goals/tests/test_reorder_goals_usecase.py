"""ReorderGoalsUseCase 単体テスト（Repositoryをモック）。"""

from unittest.mock import MagicMock

from apps.goals.application.usecases.reorder_goals_usecase import ReorderGoalsUseCase


class TestReorderGoalsUseCase:
    def test_execute_delegates_to_repository(self) -> None:
        repo = MagicMock()
        usecase = ReorderGoalsUseCase(repo)
        usecase.execute(user_id=1, ordered_ids=[3, 1, 2])
        repo.reorder.assert_called_once_with(1, [3, 1, 2])

    def test_execute_with_empty_list(self) -> None:
        repo = MagicMock()
        usecase = ReorderGoalsUseCase(repo)
        usecase.execute(user_id=1, ordered_ids=[])
        repo.reorder.assert_called_once_with(1, [])
