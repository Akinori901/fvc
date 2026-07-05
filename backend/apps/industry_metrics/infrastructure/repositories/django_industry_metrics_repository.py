"""業界指標リポジトリ Django実装。"""

from __future__ import annotations

from apps.industry_metrics.domain.entities import IndustryMetricsEntity
from apps.industry_metrics.domain.repositories import IndustryMetricsRepository
from apps.industry_metrics.models import IndustryMetrics


class DjangoIndustryMetricsRepository(IndustryMetricsRepository):
    def find_by_sector(self, sector: str) -> IndustryMetricsEntity | None:
        obj = IndustryMetrics.objects.filter(sector=sector).first()
        return self._to_entity(obj) if obj else None

    def upsert(self, entity: IndustryMetricsEntity) -> IndustryMetricsEntity:
        obj, _ = IndustryMetrics.objects.update_or_create(
            sector=entity.sector,
            defaults={
                "min_roe": entity.min_roe,
                "max_roe": entity.max_roe,
                "note": entity.note or "",
            },
        )
        return self._to_entity(obj)

    def list_all(self) -> list[IndustryMetricsEntity]:
        return [self._to_entity(o) for o in IndustryMetrics.objects.all().order_by("sector")]

    def _to_entity(self, obj: IndustryMetrics) -> IndustryMetricsEntity:
        return IndustryMetricsEntity(
            id=obj.pk,
            sector=obj.sector,
            min_roe=obj.min_roe,
            max_roe=obj.max_roe,
            note=obj.note or None,
        )
