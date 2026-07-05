from django.contrib import admin

from apps.ai.infrastructure.models import AiAnalysisLog, UserAiConfig


@admin.register(UserAiConfig)
class UserAiConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "provider", "model", "is_enabled", "updated_at"]
    list_filter = ["provider", "is_enabled"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AiAnalysisLog)
class AiAnalysisLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "stock", "question_type", "model_used", "is_success", "created_at"]
    list_filter = ["question_type", "is_success", "model_used"]
    search_fields = ["user__username", "stock__code"]
    readonly_fields = ["created_at"]
