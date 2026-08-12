"""スクリーニングキャッシュを無効化するコマンド。

DB キャッシュテーブルから screening:* キーを削除する。
株価同期完了後に実行（EventBridge Scheduler または sync_prices コマンド末尾から呼び出し）。
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "スクリーニングキャッシュを無効化"

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with connection.cursor() as cursor:
                # django_cache テーブルから screening:* キーを削除
                cursor.execute(
                    "DELETE FROM django_cache WHERE cache_key LIKE %s",
                    ["%:1:screening:%"],
                )
                deleted_count = cursor.rowcount
            self.stdout.write(self.style.SUCCESS(f"スクリーニングキャッシュ {deleted_count} 件を削除しました"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"キャッシュ削除エラー: {e}"))
