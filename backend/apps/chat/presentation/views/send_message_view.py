"""チャットメッセージ送信ビュー。

POST /api/chat/messages/
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.domain.exceptions import AiApiKeyInvalidError
from apps.chat.application.dto import SendMessageRequestDTO
from apps.chat.domain.exceptions import (
    ChatConfigMissingError,
    ChatDailyLimitExceededError,
    ChatSessionNotFoundError,
)
from apps.chat.presentation.serializers import SendMessageRequestSerializer
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request

logger = logging.getLogger(__name__)


class SendMessageView(APIView):
    """ログインユーザーのみ。BYOK 必須。"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SendMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assert isinstance(request.user.id, int)
        req_dto = SendMessageRequestDTO(
            user_id=request.user.id,
            user_message=serializer.validated_data["user_message"],
            session_id=serializer.validated_data.get("session_id"),
            use_admin_key=serializer.validated_data.get("use_admin_key", False),
        )

        usecase = container.send_chat_message_usecase()
        try:
            result = usecase.execute(req_dto, is_superuser=bool(request.user.is_superuser))
        except ChatConfigMissingError as exc:
            return Response(
                {"detail": str(exc), "setup_url": "/settings"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ChatDailyLimitExceededError as exc:
            return Response(
                {
                    "detail": str(exc),
                    "limit": exc.limit,
                    "current": exc.current,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except ChatSessionNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except AiApiKeyInvalidError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (TimeoutError, RuntimeError) as exc:
            logger.warning("チャット LLM 呼び出し失敗: %s", exc)
            return Response(
                {"detail": f"AIサービスが一時的に利用できません: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "session_id": result.session_id,
                "assistant_message": result.assistant_message,
                "provider": result.provider,
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "iterations": result.iterations,
                "truncated": result.truncated,
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "succeeded": tc.succeeded,
                    }
                    for tc in result.tool_calls_summary
                ],
            }
        )
