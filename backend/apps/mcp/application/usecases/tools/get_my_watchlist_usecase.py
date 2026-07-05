"""ウォッチリスト取得ツール UseCase。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.portfolios.domain.repositories import WatchlistRepository


class GetMyWatchlistToolUseCase:
    """ウォッチ銘柄一覧（要 user_id）。

    銘柄ごとの詳細サマリは Claude/ChatGPT が `get_stock_summary` を別途呼ぶ前提。
    本ツールは「どの銘柄をウォッチしているか」のリストだけ返す。
    """

    def __init__(self, watchlist_repo: WatchlistRepository) -> None:
        self._watchlist_repo = watchlist_repo

    def execute(self, *, user_id: int) -> dict[str, Any]:
        items = self._watchlist_repo.find_by_user(user_id)
        return {
            "count": len(items),
            "items": [
                {
                    "code": item.stock_code,
                    "name": item.stock_name,
                    "memo": item.memo,
                }
                for item in items
            ],
        }
