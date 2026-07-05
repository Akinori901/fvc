"""管理者昇格コマンド。

Usage:
    python manage.py promote_superuser <email>

指定 email の `auth_user` を `is_superuser=True` / `is_staff=True` に更新する。
本番では Worker Lambda 経由で実行する想定 (CD パイプラインに組み込まれない手動コマンド)。
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "指定 email の auth_user を superuser に昇格させる"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email", type=str, help="昇格対象の email")

    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"]
        user_model = get_user_model()
        try:
            user = user_model._default_manager.get(email__iexact=email)  # noqa: SLF001
        except user_model.DoesNotExist as exc:
            msg = f"email {email} のユーザーが存在しません"
            raise CommandError(msg) from exc

        if user.is_superuser and user.is_staff:
            self.stdout.write(self.style.WARNING(f"{email} は既に superuser です"))
            return

        user.is_superuser = True
        user.is_staff = True
        user.save(update_fields=["is_superuser", "is_staff"])
        self.stdout.write(self.style.SUCCESS(f"{email} を superuser に昇格しました"))
