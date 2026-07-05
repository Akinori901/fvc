"""開発用初期データ投入コマンド。

Usage:
    python manage.py seed          # 全シードを実行
    python manage.py seed --admin  # 管理者ユーザーのみ
"""

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandParser

User = get_user_model()

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin1234"


class Command(BaseCommand):
    help = "開発用の初期データを投入する"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--admin",
            action="store_true",
            help="管理者ユーザーのみ作成",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self._seed_admin()

        if not options["admin"]:
            self._seed_api_config()

        self.stdout.write(self.style.SUCCESS("シード完了"))

    def _seed_admin(self) -> None:
        if User.objects.filter(username=ADMIN_USERNAME).exists():
            self.stdout.write(f"  [skip] ユーザー '{ADMIN_USERNAME}' は既に存在します")
            return

        User.objects.create_superuser(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
        )
        self.stdout.write(self.style.SUCCESS(f"  [created] 管理者ユーザー: {ADMIN_USERNAME} / {ADMIN_PASSWORD}"))

    def _seed_api_config(self) -> None:
        from apps.stocks.models import ApiConfig

        config, created = ApiConfig.objects.get_or_create(
            provider="jquants",
            defaults={
                "is_enabled": False,
                "plan": "free",
                "api_key": "",
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("  [created] J-Quants API設定 (free/無効)"))
        else:
            self.stdout.write("  [skip] J-Quants API設定は既に存在します")
