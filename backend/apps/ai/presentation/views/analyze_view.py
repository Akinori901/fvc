"""個別株AI分析ビュー。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.application.dto import AnalysisRequestDTO
from apps.ai.domain.exceptions import (
    AiApiKeyInvalidError,
    AiConfigNotFoundError,
    AiRateLimitExceededError,
)
from apps.ai.presentation.serializers import AnalyzeRequestSerializer
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class StockAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, code: str) -> Response:
        serializer = AnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert isinstance(request.user.id, int)
        req_dto = AnalysisRequestDTO(
            user_id=request.user.id,
            stock_code=code,
            question_type=serializer.validated_data["question_type"],
            custom_question=serializer.validated_data.get("custom_question", ""),
            expert_role=serializer.validated_data.get("expert_role", "general"),
        )

        usecase = container.analyze_stock_usecase()
        try:
            result = usecase.execute(req_dto)
        except AiConfigNotFoundError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except AiRateLimitExceededError as exc:
            return Response(
                {
                    "detail": (
                        f"リクエストが多すぎます。1分後に再試行してください。({exc.current_count}/{exc.max_per_minute})"
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except AiApiKeyInvalidError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (TimeoutError, RuntimeError) as exc:
            return Response(
                {"detail": f"AI分析サービスが一時的に利用できません: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "analysis": result.analysis,
                "model": result.model,
                "generated_at": result.generated_at.isoformat(),
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
            }
        )
