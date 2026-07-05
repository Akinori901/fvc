"""FX分析取得ユースケース。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..dto import fx_analysis_to_dict

if TYPE_CHECKING:
    from ..services.fx_analysis_service import FxAnalysisService


class GetFxAnalysisUseCase:
    """GET /api/fx/analysis/ のビジネスロジック"""

    def __init__(self, analysis_service: FxAnalysisService) -> None:
        self._analysis_service = analysis_service

    def execute(self) -> dict[str, Any]:
        result = self._analysis_service.analyze()
        return fx_analysis_to_dict(result)
