"""日次急騰急落集計の UseCase。

`StockRepository` + `PriceRepository` から全アクティブ JP 銘柄の直近価格を取得し、
`compute_movers_service` で集計、`DailyMoversRepository.bulk_replace` で t_daily_movers に
保存する。EventBridge / manage.py compute_movers から呼ばれる。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.stocks.application.services.compute_movers_service import MoversInput, compute_one

if TYPE_CHECKING:
    import datetime

    from apps.stocks.domain.entities import DailyMoversEntity
    from apps.stocks.domain.repositories import (
        DailyMoversRepository,
        PriceRepository,
        StockRepository,
    )


logger = logging.getLogger(__name__)


# 過去 N 営業日分を取得（出来高 20 日平均 + 当日 + 前日のマージンを確保）
_PRICE_FETCH_LIMIT = 25


class ComputeDailyMoversUseCase:
    """全アクティブ JP 銘柄の前日比 / 出来高比 / UL/LL を t_daily_movers に再生成する。"""

    def __init__(
        self,
        stock_repo: StockRepository,
        price_repo: PriceRepository,
        movers_repo: DailyMoversRepository,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._movers_repo = movers_repo

    def execute(
        self,
        *,
        target_date: datetime.date | None = None,
        market_type: str = "JP",
    ) -> dict[str, int]:
        """全アクティブ JP 銘柄を対象に movers を再計算し、t_daily_movers を target_date 単位で
        トランザクション内で完全に置き換える。

        Args:
            target_date: 集計対象日（None = 各銘柄の最新営業日）
            market_type: 対象市場

        Returns:
            {"computed": N, "saved": M, "skipped": K}
        """
        stocks = self._stock_repo.find_by_market_type(market_type, active_only=True)
        logger.info("compute_movers 開始: %d 銘柄 (target_date=%s)", len(stocks), target_date)

        # 一括取得（全銘柄の直近 N 件）
        recent_prices_map = self._price_repo.find_all_recent_prices(limit=_PRICE_FETCH_LIMIT)

        entities: list[DailyMoversEntity] = []
        skipped = 0
        resolved_date: datetime.date | None = target_date
        for stock in stocks:
            if stock.id is None:
                skipped += 1
                continue
            prices = recent_prices_map.get(stock.id, [])
            if not prices:
                skipped += 1
                continue
            output = compute_one(
                MoversInput(stock_id=stock.id, prices_desc=prices),
                target_date=target_date,
            )
            if output is None:
                skipped += 1
                continue

            entities.append(_to_entity(output))
            if resolved_date is None:
                resolved_date = output.date

        if resolved_date is None or not entities:
            logger.info("compute_movers: 集計対象なし")
            return {"computed": 0, "saved": 0, "skipped": skipped}

        saved = self._movers_repo.bulk_replace(resolved_date, entities)
        logger.info(
            "compute_movers 完了: %d 銘柄集計, %d 保存, %d skip (date=%s)",
            len(entities),
            saved,
            skipped,
            resolved_date,
        )
        return {"computed": len(entities), "saved": saved, "skipped": skipped}


def _to_entity(output: object) -> DailyMoversEntity:
    from apps.stocks.domain.entities import DailyMoversEntity

    return DailyMoversEntity(
        stock_id=output.stock_id,  # type: ignore[attr-defined]
        date=output.date,  # type: ignore[attr-defined]
        close_price=output.close_price,  # type: ignore[attr-defined]
        prev_close=output.prev_close,  # type: ignore[attr-defined]
        change_pct=output.change_pct,  # type: ignore[attr-defined]
        volume=output.volume,  # type: ignore[attr-defined]
        volume_ratio_20d=output.volume_ratio_20d,  # type: ignore[attr-defined]
        is_limit_up=output.is_limit_up,  # type: ignore[attr-defined]
        is_limit_down=output.is_limit_down,  # type: ignore[attr-defined]
    )
