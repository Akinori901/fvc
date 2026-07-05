from django.contrib import admin

from .models import Valuation


@admin.register(Valuation)
class ValuationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("stock", "calculated_at", "fair_value", "current_price", "is_undervalued")
    list_filter = ("is_undervalued", "calculated_at")
