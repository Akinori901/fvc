"""本番環境設定（Lambda + RDS）"""

from .base import *  # noqa: F401, F403

DEBUG = False

# --- Database (RDS) ---
# Lambda 環境変数は DATABASE_* を使用
DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DATABASE_NAME", default="fair_value_calculator"),  # noqa: F405
        "USER": env("DATABASE_USER", default="fvc_admin"),  # noqa: F405
        "PASSWORD": env("DATABASE_PASSWORD"),  # noqa: F405
        "HOST": env("DATABASE_HOST"),  # noqa: F405
        "PORT": env("DATABASE_PORT", default="3306"),  # noqa: F405
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# --- Cache (DB-backed cache for Lambda) ---
CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 1800,  # 30分
        "OPTIONS": {
            "MAX_ENTRIES": 200,
        },
    }
}

# CORS: CloudFront 経由のためワイルドカード許可
CORS_ALLOW_ALL_ORIGINS = True

# セキュリティ設定
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 静的ファイル（Lambda環境ではS3等を使用）
STATIC_URL = env("STATIC_URL", default="/static/")  # noqa: F405
