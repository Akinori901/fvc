from django.contrib import admin

from .models import WatchlistItem


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "stock", "memo", "created_at")
    list_filter = ("user",)
    search_fields = ("stock__code", "stock__name")
