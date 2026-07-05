from django.contrib import admin

from .models import ApiConfig, Stock, StockFinancial, StockPrice, SyncLog


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("code", "name", "market", "market_type", "sector", "is_active", "updated_at")
    search_fields = ("code", "name")
    list_filter = ("market", "market_type", "is_active", "sector")


@admin.register(StockFinancial)
class StockFinancialAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("stock", "fiscal_year", "bps", "eps", "roe", "revenue", "operating_income")
    list_filter = ("fiscal_year",)


@admin.register(StockPrice)
class StockPriceAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("stock", "date", "close_price", "pbr", "volume")
    list_filter = ("date",)


@admin.register(ApiConfig)
class ApiConfigAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("provider", "is_enabled", "plan", "updated_at")
    list_filter = ("is_enabled",)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "sync_type",
        "provider",
        "market",
        "status",
        "started_at",
        "finished_at",
        "total_count",
        "success_count",
        "error_count",
    )
    list_filter = ("sync_type", "provider", "market", "status")
    readonly_fields = (
        "sync_type",
        "provider",
        "market",
        "status",
        "started_at",
        "finished_at",
        "total_count",
        "success_count",
        "error_count",
        "error_details",
    )
