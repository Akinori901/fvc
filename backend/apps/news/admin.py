from django.contrib import admin

from .models import NewsAiAnalysis, NewsArticle, NewsKeyword, NewsStockLink


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "category", "source", "title", "published_at", "importance_score")
    list_filter = ("category", "source", "language")
    search_fields = ("title", "publisher")
    date_hierarchy = "published_at"


@admin.register(NewsStockLink)
class NewsStockLinkAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("news", "stock", "relevance_score", "matched_by")
    list_filter = ("matched_by",)


@admin.register(NewsAiAnalysis)
class NewsAiAnalysisAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("news", "user", "impact_direction", "impact_period", "confidence", "model_used", "generated_at")
    list_filter = ("impact_direction", "impact_period", "confidence")


@admin.register(NewsKeyword)
class NewsKeywordAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("category", "keyword", "query", "is_active", "sort_order")
    list_filter = ("category", "is_active")
