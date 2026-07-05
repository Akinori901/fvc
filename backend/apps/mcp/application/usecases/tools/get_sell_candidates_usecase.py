"""売却候補銘柄抽出ツール UseCase。

ユーザーの保有銘柄を取得し、ScreeningUseCase で各銘柄を評価して
保守的な 3 条件すべてに該当する銘柄を売却候補として返す。

判定ロジック（3 条件 AND）:
1. evaluation_zone == "very_expensive"
2. momentum_signal in ("sell", "caution")
3. roe_trend == "declining"
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.portfolios.domain.repositories import AccountSnapshotRepository
    from apps.stocks.application.usecases.screening_usecase import (
        ScreeningResult,
        ScreeningUseCase,
    )


_DEFAULT_GROWTH_RATE = Decimal("0.02")


class GetSellCandidatesToolUseCase:
    """保有銘柄から売却候補を抽出する（要 user_id、保守的判定）。"""

    def __init__(
        self,
        snapshot_repo: AccountSnapshotRepository,
        screening_usecase: ScreeningUseCase,
    ) -> None:
        self._snapshot_repo = snapshot_repo
        self._screening_usecase = screening_usecase

    def execute(self, *, user_id: int) -> dict[str, Any]:
        snapshots = self._snapshot_repo.find_latest_by_user(user_id)

        codes: set[str] = set()
        for snap in snapshots:
            for h in snap.holdings:
                if h.ticker_code:
                    codes.add(h.ticker_code)

        candidates: list[dict[str, Any]] = []
        evaluated_count = 0
        for code in sorted(codes):
            results = self._screening_usecase.execute(
                growth_rate=_DEFAULT_GROWTH_RATE,
                code=code,
                include_inactive=True,
            )
            if not results:
                continue
            evaluated_count += 1
            result = results[0]
            if _is_sell_candidate(result):
                candidates.append(_to_dto(result))

        return {
            "count": len(candidates),
            "evaluated_holdings_count": evaluated_count,
            "candidates": candidates,
            "judgment_criteria": (
                "保守的: evaluation_zone == very_expensive AND "
                "momentum_signal in (sell, caution) AND roe_trend == declining"
            ),
        }


def _is_sell_candidate(r: ScreeningResult) -> bool:
    if r.evaluation_zone != "very_expensive":
        return False
    if r.momentum_signal not in ("sell", "caution"):
        return False
    return r.roe_trend == "declining"


def _to_dto(r: ScreeningResult) -> dict[str, Any]:
    return {
        "code": r.code,
        "name": r.name,
        "sector": r.sector,
        "latest_price": _decimal_or_none(r.latest_price),
        "current_pbr": _decimal_or_none(r.current_pbr),
        "fair_pbr": _decimal_or_none(r.fair_pbr),
        "fair_value": _decimal_or_none(r.fair_value),
        "discount_rate": _decimal_or_none(r.discount_rate),
        "evaluation_zone": r.evaluation_zone,
        "momentum_signal": r.momentum_signal,
        "roe_trend": r.roe_trend,
        "trigger_reasons": [r.evaluation_zone, r.momentum_signal, "roe_declining"],
    }


def _decimal_or_none(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None
