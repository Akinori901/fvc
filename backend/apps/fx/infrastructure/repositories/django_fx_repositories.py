"""FX リポジトリ Django ORM 実装。"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from ...domain.entities import FxRateEntity, InterestRateEntity, MacroIndicatorEntity
from ...domain.repositories import FxRateRepository, InterestRateRepository, MacroIndicatorRepository
from ..models import FxRate, InterestRate, MacroIndicator

if TYPE_CHECKING:
    from datetime import date


class DjangoFxRateRepository(FxRateRepository):
    """為替レートリポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: FxRate) -> FxRateEntity:
        return FxRateEntity(
            id=obj.pk,
            date=obj.date,
            pair=obj.pair,
            close_rate=Decimal(str(obj.close_rate)),
        )

    def find_all(self, pair: str = "USDJPY", limit: int | None = None) -> list[FxRateEntity]:
        qs = FxRate.objects.filter(pair=pair).order_by("date")
        if limit:
            qs = qs[:limit]
        return [self._to_entity(obj) for obj in qs]

    def find_latest(self, pair: str = "USDJPY") -> FxRateEntity | None:
        obj = FxRate.objects.filter(pair=pair).order_by("-date").first()
        return self._to_entity(obj) if obj else None

    def find_latest_date(self, pair: str = "USDJPY") -> date | None:
        obj = FxRate.objects.filter(pair=pair).order_by("-date").values_list("date", flat=True).first()
        return obj

    def bulk_save(self, entities: list[FxRateEntity]) -> int:
        if not entities:
            return 0
        objs = [FxRate(pair=e.pair, date=e.date, close_rate=e.close_rate) for e in entities]
        created = FxRate.objects.bulk_create(objs, ignore_conflicts=True)
        return len(created)


class DjangoInterestRateRepository(InterestRateRepository):
    """金利リポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: InterestRate) -> InterestRateEntity:
        return InterestRateEntity(
            id=obj.pk,
            date=obj.date,
            country=obj.country,
            rate_type=obj.rate_type,
            rate=Decimal(str(obj.rate)),
        )

    def find_all(self, country: str, rate_type: str = "10Y") -> list[InterestRateEntity]:
        qs = InterestRate.objects.filter(country=country, rate_type=rate_type).order_by("date")
        return [self._to_entity(obj) for obj in qs]

    def find_latest(self, country: str, rate_type: str = "10Y") -> InterestRateEntity | None:
        obj = InterestRate.objects.filter(country=country, rate_type=rate_type).order_by("-date").first()
        return self._to_entity(obj) if obj else None

    def find_latest_date(self, country: str, rate_type: str = "10Y") -> date | None:
        obj = (
            InterestRate.objects.filter(country=country, rate_type=rate_type)
            .order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        return obj

    def bulk_save(self, entities: list[InterestRateEntity]) -> int:
        if not entities:
            return 0
        objs = [InterestRate(country=e.country, rate_type=e.rate_type, date=e.date, rate=e.rate) for e in entities]
        created = InterestRate.objects.bulk_create(objs, ignore_conflicts=True)
        return len(created)


class DjangoMacroIndicatorRepository(MacroIndicatorRepository):
    """マクロ指標リポジトリ Django ORM 実装"""

    @staticmethod
    def _to_entity(obj: MacroIndicator) -> MacroIndicatorEntity:
        return MacroIndicatorEntity(
            id=obj.pk,
            indicator_type=obj.indicator_type,
            value=Decimal(str(obj.value)),
            year=obj.year,
            source=obj.source,
        )

    def find_latest(self, indicator_type: str) -> MacroIndicatorEntity | None:
        obj = MacroIndicator.objects.filter(indicator_type=indicator_type).order_by("-year").first()
        return self._to_entity(obj) if obj else None

    def save(self, entity: MacroIndicatorEntity) -> MacroIndicatorEntity:
        obj, _ = MacroIndicator.objects.update_or_create(
            indicator_type=entity.indicator_type,
            year=entity.year,
            defaults={"value": entity.value, "source": entity.source},
        )
        return self._to_entity(obj)
