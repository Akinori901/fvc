"""Django 共通設定"""

import os
from pathlib import Path

import environ

# backend/ ディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# django-environ で .env 読み込み
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# --- Application definition ---

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    # Local apps
    "apps.core",
    "apps.stocks",
    "apps.valuations",
    "apps.portfolios",
    "apps.ai",
    "apps.fx",
    "apps.paper_trading",
    "apps.goals",
    "apps.industry_metrics",
    "apps.news",
    "apps.mcp",
    "apps.chat",
    "apps.auth_cognito",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DATABASE", default="fair_value_calculator"),
        "USER": env("MYSQL_USER", default="fvc_user"),
        "PASSWORD": env("MYSQL_PASSWORD", default="fvc_password"),
        "HOST": env("MYSQL_HOST", default="db"),
        "PORT": env("MYSQL_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# --- Password validation ---

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ---

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

# --- Static files ---

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Default primary key field type ---

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Cognito JWT (Bearer 形式、Cognito 発行) を検証する。
        # CognitoJWTAuthentication.authenticate() は iss claim を peek して
        # Cognito JWT 以外は None を返し、次の認証クラスにフォールバックさせる。
        "apps.auth_cognito.presentation.drf_authentication.CognitoJWTAuthentication",
        # MCP API キー (`Authorization: Bearer fvc_mcp_xxx`)
        "apps.mcp.presentation.auth.McpApiKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DATE_FORMAT": "%Y-%m-%d",
}

# --- Cognito (OAuth) ---
# 設計書: docs/design/cognito-oauth-migration.md
# Phase D で旧 dj-rest-auth / django-allauth / djangorestframework-simplejwt は
# 全て撤去済み。認証は Cognito (JWT 検証) と MCP API キーの 2 経路のみ。

COGNITO_USER_POOL_ID = env("COGNITO_USER_POOL_ID", default="")
COGNITO_REGION = env("COGNITO_REGION", default="ap-northeast-1")
COGNITO_WEB_CLIENT_ID = env("COGNITO_WEB_CLIENT_ID", default="")
COGNITO_GPT_CLIENT_ID = env("COGNITO_GPT_CLIENT_ID", default="")
COGNITO_DOMAIN_PREFIX = env("COGNITO_DOMAIN_PREFIX", default="")

# JWT 検証時に許可する aud (client_id) の集合。空文字は除外。
COGNITO_ALLOWED_CLIENT_IDS = tuple(
    client_id for client_id in (COGNITO_WEB_CLIENT_ID, COGNITO_GPT_CLIENT_ID) if client_id
)

# JWT issuer (token の iss claim と完全一致を要求する)
COGNITO_JWT_ISSUER = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}" if COGNITO_USER_POOL_ID else ""
)

# JWKS URL (公開鍵取得用)
COGNITO_JWKS_URL = f"{COGNITO_JWT_ISSUER}/.well-known/jwks.json" if COGNITO_USER_POOL_ID else ""

# --- CORS ---
# 開発環境・本番環境で個別に設定

# --- Logging ---

LOG_DIR = os.environ.get("LOG_DIR", "/tmp")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "django.log"),
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
