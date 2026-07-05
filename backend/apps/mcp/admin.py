from django.contrib import admin

from .models import McpApiKey


@admin.register(McpApiKey)
class McpApiKeyAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "label", "key_prefix", "is_active", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "label", "key_prefix")
    readonly_fields = ("key_prefix", "key_hash", "last_used_at", "created_at", "updated_at")
