"""Phase D で残骸となった旧 dj-rest-auth / allauth / sites 関連テーブルを drop する。

背景:
- Phase D (PR #74/#75) で INSTALLED_APPS から allauth / dj_rest_auth /
  django.contrib.sites を削除した
- ただし既存テーブル (account_*, socialaccount_*, django_site) と
  django_migrations の孤児レコードは残骸として残っていた
- 全テーブル 0 件であることを確認済み (memory/feature_cognito_phase_d.md)
- 既存コードからの参照ゼロを Phase D で確認済み

本マイグレーションで:
1. 7 テーブルを DROP TABLE IF EXISTS で削除
2. django_migrations から account / socialaccount / sites の記録を削除

ロールバック (reverse_sql) は noop。理由:
- テーブル定義は外部 package (allauth/sites) のものなので自前で書くのは
  メンテ負担。data も全件 0 件なので復元する意味がない
- 万一の rollback はマイグレーション state を直接編集する想定

設計書: docs/design/cognito-oauth-migration.md
関連: memory/feature_cognito_phase_d.md
"""

from django.db import migrations

# DROP するテーブル一覧 (FK 制約があるが SET FOREIGN_KEY_CHECKS=0 で順序問題を回避)
DROP_TABLES_SQL = """
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS account_emailconfirmation;
DROP TABLE IF EXISTS account_emailaddress;
DROP TABLE IF EXISTS socialaccount_socialtoken;
DROP TABLE IF EXISTS socialaccount_socialapp_sites;
DROP TABLE IF EXISTS socialaccount_socialaccount;
DROP TABLE IF EXISTS socialaccount_socialapp;
DROP TABLE IF EXISTS django_site;
SET FOREIGN_KEY_CHECKS = 1;
"""

# django_migrations の孤児レコード削除 (account / socialaccount / sites の全マイグレーション記録)
DELETE_ORPHAN_MIGRATIONS_SQL = """
DELETE FROM django_migrations
WHERE app IN ('account', 'socialaccount', 'sites');
"""


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(
            sql=DROP_TABLES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=DELETE_ORPHAN_MIGRATIONS_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
