"""チャット機能の Django Repository 実装。"""

from __future__ import annotations

from datetime import UTC, datetime

from django.utils import timezone

from apps.chat.domain.entities import ChatMessageEntity, ChatSessionEntity
from apps.chat.domain.repositories import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from apps.chat.infrastructure.models import ChatMessage, ChatSession


class DjangoChatSessionRepository(ChatSessionRepository):
    def find_by_id(self, session_id: int) -> ChatSessionEntity | None:
        try:
            obj = ChatSession.objects.get(pk=session_id)
        except ChatSession.DoesNotExist:
            return None
        return self._to_entity(obj)

    def list_by_user_id(self, user_id: int, limit: int = 50) -> list[ChatSessionEntity]:
        qs = ChatSession.objects.filter(user_id=user_id).order_by("-last_message_at")[:limit]
        return [self._to_entity(o) for o in qs]

    def save(self, session: ChatSessionEntity) -> ChatSessionEntity:
        if session.id is None:
            obj = ChatSession.objects.create(
                user_id=session.user_id,
                provider=session.provider,
                title=session.title,
            )
        else:
            obj = ChatSession.objects.get(pk=session.id)
            obj.provider = session.provider
            obj.title = session.title
            obj.save(update_fields=["provider", "title"])
        return self._to_entity(obj)

    def touch(self, session_id: int) -> None:
        ChatSession.objects.filter(pk=session_id).update(last_message_at=timezone.now())

    def delete(self, session_id: int) -> None:
        ChatSession.objects.filter(pk=session_id).delete()

    @staticmethod
    def _to_entity(obj: ChatSession) -> ChatSessionEntity:
        return ChatSessionEntity(
            id=obj.pk,
            user_id=obj.user_id,
            provider=obj.provider,
            title=obj.title,
            started_at=obj.started_at,
            last_message_at=obj.last_message_at,
        )


class DjangoChatMessageRepository(ChatMessageRepository):
    def list_by_session_id(self, session_id: int, limit: int | None = None) -> list[ChatMessageEntity]:
        qs = ChatMessage.objects.filter(session_id=session_id).order_by("created_at")
        if limit is not None:
            # 「最新 N 件」を created_at 昇順で返したい場合は末尾 N を取る
            ids = list(qs.values_list("pk", flat=True))[-limit:]
            qs = ChatMessage.objects.filter(pk__in=ids).order_by("created_at")
        return [self._to_entity(o) for o in qs]

    def save(self, message: ChatMessageEntity) -> ChatMessageEntity:
        obj = ChatMessage.objects.create(
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            tool_name=message.tool_name or "",
            tool_args=dict(message.tool_args) if message.tool_args else {},
            tool_result=dict(message.tool_result) if message.tool_result else {},
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            model_used=message.model_used,
            provider=message.provider,
        )
        return self._to_entity(obj)

    def count_by_user_since(self, user_id: int, since: datetime) -> int:
        # since が naive なら UTC とみなす（ローカルで datetime.now() を渡された場合の保険）
        if since.tzinfo is None:
            since = since.replace(tzinfo=UTC)
        return ChatMessage.objects.filter(
            session__user_id=user_id,
            role="user",
            created_at__gte=since,
        ).count()

    @staticmethod
    def _to_entity(obj: ChatMessage) -> ChatMessageEntity:
        return ChatMessageEntity(
            id=obj.pk,
            session_id=obj.session_id,
            role=obj.role,
            content=obj.content,
            tool_name=obj.tool_name or None,
            tool_args=dict(obj.tool_args) if obj.tool_args else {},
            tool_result=dict(obj.tool_result) if obj.tool_result else {},
            prompt_tokens=obj.prompt_tokens,
            completion_tokens=obj.completion_tokens,
            model_used=obj.model_used,
            provider=obj.provider,
            created_at=obj.created_at,
        )
