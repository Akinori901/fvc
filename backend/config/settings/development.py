"""開発環境設定"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# CORS: 開発環境はフロントエンドからの全リクエストを許可
CORS_ALLOW_ALL_ORIGINS = True

# --- Cache (In-memory cache for local development) ---
CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# DRF: 開発時はBrowsable APIも有効化
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
