"""テスト環境設定"""

from .base import *  # noqa: F401, F403

DEBUG = True

# テスト用DB（MySQLのまま、テスト実行時に自動作成）
DATABASES["default"]["TEST"] = {  # noqa: F405
    "NAME": "test_fair_value_calculator",
    "CHARSET": "utf8mb4",
    "COLLATION": "utf8mb4_unicode_ci",
}

# テスト高速化: パスワードハッシュを軽量化
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
