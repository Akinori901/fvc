"""FX分析 View。"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from config import container


class FxAnalysisView(APIView):
    """GET /api/fx/analysis/ — FX分析結果を返す"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        usecase = container.get_fx_analysis_usecase()
        result = usecase.execute()
        return Response(result)
