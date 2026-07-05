"""Cognito 認証の Django Repository 実装。"""

from __future__ import annotations

from django.utils import timezone

from apps.auth_cognito.domain.entities import CognitoLinkEntity, UserAllowedEmailEntity
from apps.auth_cognito.domain.repositories import (
    CognitoLinkRepository,
    UserAllowedEmailRepository,
)
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail


class DjangoCognitoLinkRepository(CognitoLinkRepository):
    def find_by_sub(self, cognito_sub: str) -> CognitoLinkEntity | None:
        try:
            obj = CognitoLink.objects.get(cognito_sub=cognito_sub)
        except CognitoLink.DoesNotExist:
            return None
        return self._to_entity(obj)

    def find_by_id(self, link_id: int) -> CognitoLinkEntity | None:
        try:
            obj = CognitoLink.objects.get(pk=link_id)
        except CognitoLink.DoesNotExist:
            return None
        return self._to_entity(obj)

    def save(self, link: CognitoLinkEntity) -> CognitoLinkEntity:
        if link.id is None:
            obj = CognitoLink.objects.create(
                cognito_sub=link.cognito_sub,
                user_id=link.user_id,
                provider=link.provider,
                cognito_email=link.cognito_email,
                last_signed_in_at=link.last_signed_in_at,
            )
        else:
            obj = CognitoLink.objects.get(pk=link.id)
            obj.provider = link.provider
            obj.cognito_email = link.cognito_email
            obj.last_signed_in_at = link.last_signed_in_at
            obj.save(update_fields=["provider", "cognito_email", "last_signed_in_at", "updated_at"])
        return self._to_entity(obj)

    def touch_last_signed_in(self, link_id: int) -> None:
        CognitoLink.objects.filter(pk=link_id).update(last_signed_in_at=timezone.now())

    def list_all(self) -> list[CognitoLinkEntity]:
        return [self._to_entity(obj) for obj in CognitoLink.objects.all().order_by("id")]

    def delete(self, link_id: int) -> None:
        CognitoLink.objects.filter(pk=link_id).delete()

    @staticmethod
    def _to_entity(obj: CognitoLink) -> CognitoLinkEntity:
        return CognitoLinkEntity(
            id=obj.pk,
            cognito_sub=obj.cognito_sub,
            user_id=obj.user_id,
            provider=obj.provider,
            cognito_email=obj.cognito_email,
            last_signed_in_at=obj.last_signed_in_at,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class DjangoUserAllowedEmailRepository(UserAllowedEmailRepository):
    def find_by_email(self, email: str) -> UserAllowedEmailEntity | None:
        try:
            obj = UserAllowedEmail.objects.get(email__iexact=email)
        except UserAllowedEmail.DoesNotExist:
            return None
        return self._to_entity(obj)

    def find_by_id(self, allowed_id: int) -> UserAllowedEmailEntity | None:
        try:
            obj = UserAllowedEmail.objects.get(pk=allowed_id)
        except UserAllowedEmail.DoesNotExist:
            return None
        return self._to_entity(obj)

    def list_by_user_id(self, user_id: int) -> list[UserAllowedEmailEntity]:
        return [self._to_entity(obj) for obj in UserAllowedEmail.objects.filter(user_id=user_id).order_by("id")]

    def list_all(self) -> list[UserAllowedEmailEntity]:
        return [self._to_entity(obj) for obj in UserAllowedEmail.objects.all().order_by("id")]

    def save(self, entity: UserAllowedEmailEntity) -> UserAllowedEmailEntity:
        if entity.id is None:
            obj = UserAllowedEmail.objects.create(
                user_id=entity.user_id,
                email=entity.email,
                label=entity.label,
            )
        else:
            obj = UserAllowedEmail.objects.get(pk=entity.id)
            obj.user_id = entity.user_id
            obj.email = entity.email
            obj.label = entity.label
            obj.save(update_fields=["user_id", "email", "label", "updated_at"])
        return self._to_entity(obj)

    def delete(self, allowed_id: int) -> None:
        UserAllowedEmail.objects.filter(pk=allowed_id).delete()

    @staticmethod
    def _to_entity(obj: UserAllowedEmail) -> UserAllowedEmailEntity:
        return UserAllowedEmailEntity(
            id=obj.pk,
            user_id=obj.user_id,
            email=obj.email,
            label=obj.label,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
