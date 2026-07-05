"""おすすめ銘柄スナップショット生成コマンド。

RecommendationUseCase を実行し、結果を t_recommendation_snapshots に保存する。
平日 9:00 JST に EventBridge 経由で Worker Lambda 上で実行される。
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "日本株おすすめスナップショットを生成・保存する"

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import RecommendationSnapshot
        from config.container import recommendation_usecase

        self.stdout.write("おすすめスナップショット生成を開始します...")
        usecase = recommendation_usecase()
        result = usecase.execute()

        objs: list[RecommendationSnapshot] = []
        for category, items in (
            ("long_term", result.long_term),
            ("day_trade", result.day_trade),
            ("range_bound", result.range_bound),
        ):
            for rank, rec in enumerate(items, start=1):
                if not rec.stock_id:
                    continue
                objs.append(
                    RecommendationSnapshot(
                        category=category,
                        rank=rank,
                        stock_id=rec.stock_id,
                        latest_price=rec.latest_price,
                        metrics=rec.metrics,
                        score=rec.score,
                    )
                )

        with transaction.atomic():
            RecommendationSnapshot.objects.all().delete()
            RecommendationSnapshot.objects.bulk_create(objs)

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: {len(objs)}件保存 "
                f"(long_term={len(result.long_term)}, "
                f"day_trade={len(result.day_trade)}, "
                f"range_bound={len(result.range_bound)})"
            )
        )
