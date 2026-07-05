"""FX 分析ツール UseCase（既存 GetFxAnalysisUseCase の薄いラップ）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.fx.application.usecases.get_fx_analysis_usecase import GetFxAnalysisUseCase


class GetFxAnalysisToolUseCase:
    """既存 FX 分析を MCP ツール用に返す（GetFxAnalysisUseCase が dict を返すので透過）。"""

    def __init__(self, fx_usecase: GetFxAnalysisUseCase) -> None:
        self._fx_usecase = fx_usecase

    def execute(self) -> dict[str, Any]:
        return self._fx_usecase.execute()
