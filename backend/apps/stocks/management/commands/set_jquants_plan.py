"""J-Quants プラン設定更新コマンド。"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "J-Quants の契約プランを更新する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--plan",
            required=True,
            choices=["free", "light", "standard", "premium"],
            help="設定するプラン名 (free / light / standard / premium)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import ApiConfig

        plan = options["plan"]

        updated = ApiConfig.objects.filter(provider="jquants").update(plan=plan)

        if updated == 0:
            raise CommandError("J-Quants の API 設定が見つかりません。管理画面から先に設定を作成してください。")

        self.stdout.write(self.style.SUCCESS(f"J-Quants のプランを '{plan}' に更新しました。"))
