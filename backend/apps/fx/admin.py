from django.contrib import admin

from .models import FxRate, InterestRate, MacroIndicator


@admin.register(FxRate)
class FxRateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("pair", "date", "close_rate")
    list_filter = ("pair",)


@admin.register(InterestRate)
class InterestRateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("country", "rate_type", "date", "rate")
    list_filter = ("country", "rate_type")


@admin.register(MacroIndicator)
class MacroIndicatorAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("indicator_type", "year", "value", "source")
    list_filter = ("indicator_type", "source")
