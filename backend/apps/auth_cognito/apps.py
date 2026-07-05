from django.apps import AppConfig


class AuthCognitoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth_cognito"
    verbose_name = "Cognito OAuth 認証"
