# Django互換 re-export（実体は infrastructure/models/ にある）
from apps.industry_metrics.infrastructure.models import IndustryMetrics

__all__ = ["IndustryMetrics"]
