"""外部API のAPIキー設定コマンド。

APIキーは引数ではなく環境変数から受け取る。
（Lambda 経由の実行時、コマンド引数は CloudWatch Logs に平文で残るため）

Usage:
    FVC_API_KEY=xxxxx manage.py set_api_key --provider edinet
"""

from __future__ import annotations

import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

_ENV_VAR = "FVC_API_KEY"


class Command(BaseCommand):
    help = f"外部APIのAPIキーを m_api_configs に登録する（キーは環境変数 {_ENV_VAR} から読む）"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--provider",
            required=True,
            help="プロバイダー名 (例: edinet / jquants / fred)",
        )
        parser.add_argument(
            "--disable",
            action="store_true",
            help="is_enabled を False にする",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.stocks.models import ApiConfig

        provider = options["provider"]
        api_key = os.environ.get(_ENV_VAR, "").strip()

        if not api_key:
            raise CommandError(f"環境変数 {_ENV_VAR} にAPIキーが設定されていません。")

        obj, created = ApiConfig.objects.update_or_create(
            provider=provider,
            defaults={"api_key": api_key, "is_enabled": not options["disable"]},
        )

        action = "登録" if created else "更新"
        # キー自体は出力しない（ログに残さないため長さのみ表示）
        self.stdout.write(
            self.style.SUCCESS(
                f"{provider} のAPIキーを{action}しました (長さ={len(obj.api_key)}, is_enabled={obj.is_enabled})"
            )
        )
