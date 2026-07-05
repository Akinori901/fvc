"""保有・ウォッチ銘柄のニュース取得ツール UseCase。

保有口座の最新スナップショットの holdings.stock_id と
ウォッチリストの stock_id を集約し、NewsArticleRepository から
一括取得する（distinct）。

AI 分析結果は本 PR では返さない（後続 PR で bulk fetch メソッド追加後に統合）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.news.domain.repositories import NewsArticleRepository
    from apps.portfolios.domain.repositories import (
        AccountSnapshotRepository,
        WatchlistRepository,
    )


_DEFAULT_DAYS = 7
_DEFAULT_LIMIT = 20


class GetMyHoldingsNewsToolUseCase:
    """ログイン中ユーザーの保有 + ウォッチ銘柄に紐づくニュースを返す（要 user_id）。"""

    def __init__(
        self,
        snapshot_repo: AccountSnapshotRepository,
        watchlist_repo: WatchlistRepository,
        article_repo: NewsArticleRepository,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._watchlist_repo = watchlist_repo
        self._article_repo = article_repo

    def execute(
        self,
        *,
        user_id: int,
        days: int = _DEFAULT_DAYS,
        min_importance: Decimal | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> dict[str, Any]:
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)
        watch_items = self._watchlist_repo.find_by_user(user_id)

        stock_ids: set[int] = set()
        for snap in snapshots:
            for h in snap.holdings:
                if h.stock_id is not None:
                    stock_ids.add(h.stock_id)
        for item in watch_items:
            if item.stock_id is not None:
                stock_ids.add(item.stock_id)

        if not stock_ids:
            return {"count": 0, "total": 0, "articles": []}

        articles, total = self._article_repo.list_articles_for_stocks(
            stock_ids=sorted(stock_ids),
            days=days,
            min_importance=min_importance,
            limit=limit,
        )

        return {
            "count": len(articles),
            "total": total,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "url": a.url,
                    "summary": a.summary,
                    "category": a.category,
                    "publisher": a.publisher,
                    "language": a.language,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "importance_score": _decimal_or_none(a.importance_score),
                }
                for a in articles
            ],
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
