"""ニュース取り込みコマンド。

Phase 1 では category="stock" のみ対応。動作確認用の --code/--limit/--max-stocks オプションを提供。
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Google News RSS からニュースを取り込み DB に保存する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--category",
            choices=["stock", "market", "fx", "earnings"],
            default="stock",
            help="取り込みカテゴリ（Phase 1 は stock のみ対応）",
        )
        parser.add_argument(
            "--code",
            type=str,
            default=None,
            help="特定銘柄のみ取り込む（動作確認用）",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="1銘柄あたりの取得件数上限",
        )
        parser.add_argument(
            "--max-stocks",
            type=int,
            default=None,
            help="全銘柄取り込み時の対象上限（デバッグ用）",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from config.container import sync_news_usecase

        category: str = options["category"]
        code: str | None = options.get("code")
        limit: int = options["limit"]
        max_stocks: int | None = options.get("max_stocks")

        self.stdout.write(
            f"ニュース取り込みを開始します (category={category}, code={code}, "
            f"limit={limit}, max_stocks={max_stocks})..."
        )

        usecase = sync_news_usecase()
        result = usecase.execute(
            category=category,
            code=code,
            limit_per_stock=limit,
            max_stocks=max_stocks,
        )

        self.stdout.write(f"  fetched: {result.fetched}")
        self.stdout.write(f"  saved (new articles): {result.saved}")
        self.stdout.write(f"  matched_links: {result.matched_links}")
        self.stdout.write(f"  skipped_irrelevant: {result.skipped_irrelevant}")
        if result.errors:
            self.stdout.write(self.style.WARNING(f"  errors: {len(result.errors)}"))
            for err in result.errors[:5]:
                self.stdout.write(self.style.WARNING(f"    - {err}"))

        self.stdout.write(self.style.SUCCESS("ニュース取り込みが完了しました"))
