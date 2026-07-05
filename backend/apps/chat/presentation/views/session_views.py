"""チャットセッション操作ビュー。

GET /api/chat/sessions/                       一覧
GET /api/chat/sessions/{session_id}/messages/ メッセージ列
DELETE /api/chat/sessions/{session_id}/       削除
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.domain.exceptions import ChatSessionNotFoundError
from config import container

if TYPE_CHECKING:
    from rest_framework.request import Request


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.list_chat_sessions_usecase()
        sessions = usecase.execute(user_id=request.user.id, limit=50)
        return Response(
            [
                {
                    "id": s.id,
                    "provider": s.provider,
                    "title": s.title,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "last_message_at": s.last_message_at.isoformat() if s.last_message_at else None,
                }
                for s in sessions
            ]
        )


class SessionMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, session_id: int) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.list_chat_messages_usecase()
        try:
            messages = usecase.execute(user_id=request.user.id, session_id=session_id)
        except ChatSessionNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "tool_name": m.tool_name,
                    "tool_args": m.tool_args,
                    "tool_result": m.tool_result,
                    "prompt_tokens": m.prompt_tokens,
                    "completion_tokens": m.completion_tokens,
                    "model_used": m.model_used,
                    "provider": m.provider,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ]
        )


class SessionDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, session_id: int) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.delete_chat_session_usecase()
        try:
            usecase.execute(user_id=request.user.id, session_id=session_id)
        except ChatSessionNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        assert isinstance(request.user.id, int)
        usecase = container.get_chat_status_usecase()
        status_dto = usecase.execute(user_id=request.user.id)
        return Response(
            {
                "has_config": status_dto.has_config,
                "is_enabled": status_dto.is_enabled,
                "provider": status_dto.provider,
                "model": status_dto.model,
                "daily_used": status_dto.daily_used,
                "daily_limit": status_dto.daily_limit,
                "daily_remaining": status_dto.daily_remaining,
            }
        )
