from django.contrib import admin

from apps.chat.infrastructure.models import ChatMessage, ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "user", "provider", "title", "started_at", "last_message_at"]
    list_filter = ["provider"]
    search_fields = ["user__username", "user__email", "title"]
    readonly_fields = ["started_at", "last_message_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["id", "session", "role", "tool_name", "model_used", "created_at"]
    list_filter = ["role", "provider", "model_used"]
    search_fields = ["content", "tool_name", "session__user__username"]
    readonly_fields = ["created_at"]
