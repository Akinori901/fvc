# Django互換 re-export（実体は infrastructure/models/ にある）
from apps.chat.infrastructure.models import ChatMessage, ChatSession

__all__ = ["ChatSession", "ChatMessage"]
