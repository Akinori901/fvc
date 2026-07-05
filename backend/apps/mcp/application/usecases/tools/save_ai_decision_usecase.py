"""AI 投資判断保存ツール UseCase。

AI クライアント (Claude / ChatGPT) が分析結果として判断種別と根拠を保存する。
保存時に get_stock_summary 相当のスナップショットを自動取得して同時に保存し、
後から「判断時点でどんな指標だったか」を振り返れるようにする。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from decimal import Decimal

    from apps.ai.domain.repositories import AiDecisionRepository
    from apps.mcp.application.usecases.tools.get_stock_summary_usecase import (
        GetStockSummaryToolUseCase,
    )
    from apps.stocks.domain.repositories import StockRepository


_VALID_DECISION_TYPES = ("buy", "sell", "hold", "watch")


class SaveAiDecisionToolUseCase:
    """AI 判断を t_ai_decisions に保存する（要 user_id）。"""

    def __init__(
        self,
        decision_repo: AiDecisionRepository,
        stock_repo: StockRepository,
        summary_usecase: GetStockSummaryToolUseCase,
    ) -> None:
        self._decision_repo = decision_repo
        self._stock_repo = stock_repo
        self._summary_usecase = summary_usecase

    def execute(
        self,
        *,
        user_id: int,
        code: str,
        decision_type: str,
        rationale: str,
        confidence: Decimal | None = None,
        ai_model: str = "",
    ) -> dict[str, Any]:
        if decision_type not in _VALID_DECISION_TYPES:
            raise ValueError(f"decision_type must be one of {_VALID_DECISION_TYPES}: {decision_type}")

        stock = self._stock_repo.find_by_code(code)
        if stock is None or stock.id is None:
            raise ValueError(f"銘柄が見つかりません: {code}")

        # 判断時点のスナップショットを撮る（get_stock_summary 結果）
        try:
            snapshot = self._summary_usecase.execute(code=code)
        except Exception:  # noqa: BLE001
            snapshot = {}

        from apps.ai.domain.entities import AiDecisionEntity

        entity = AiDecisionEntity(
            user_id=user_id,
            stock_id=stock.id,
            decision_type=decision_type,
            rationale=rationale,
            confidence=confidence,
            snapshot_indicators=snapshot,
            ai_model=ai_model,
        )
        saved = self._decision_repo.save(entity)

        return {
            "id": saved.id,
            "user_id": saved.user_id,
            "stock_code": stock.code,
            "stock_name": stock.name,
            "decision_type": saved.decision_type,
            "rationale": saved.rationale,
            "confidence": str(saved.confidence) if saved.confidence is not None else None,
            "ai_model": saved.ai_model,
            "decided_at": saved.decided_at.isoformat() if saved.decided_at else None,
            "snapshot_indicators_keys": sorted(snapshot.keys()) if snapshot else [],
        }
