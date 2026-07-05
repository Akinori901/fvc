from django.contrib import admin

from .models import IndustryMetrics


@admin.register(IndustryMetrics)
class IndustryMetricsAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("sector", "min_roe", "max_roe", "note", "updated_at")
    search_fields = ("sector",)
    ordering = ("sector",)
