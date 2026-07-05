# Django互換 re-export（実体は infrastructure/models/ にある）
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail

__all__ = ["CognitoLink", "UserAllowedEmail"]
