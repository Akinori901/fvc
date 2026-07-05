"""JitProvisionService のテスト。

JIT は「sub マッチ → allowed_emails マッチ → 紐付け、いずれも無ければ拒否」する。
1 つの auth_user に複数の Cognito identity (Cognito email + Google 等) を紐付け可能。
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.auth_cognito.application.services.jit_provision_service import JitProvisionService
from apps.auth_cognito.domain.entities import CognitoClaimsEntity
from apps.auth_cognito.domain.exceptions import UserNotAllowedError
from apps.auth_cognito.infrastructure.models import CognitoLink, UserAllowedEmail
from apps.auth_cognito.infrastructure.repositories.django_cognito_repositories import (
    DjangoCognitoLinkRepository,
    DjangoUserAllowedEmailRepository,
)

pytestmark = pytest.mark.django_db


def _make_claims(
    *,
    sub: str = "sub-1",
    email: str = "new@example.com",
    name: str = "New User",
    provider: str = "cognito",
) -> CognitoClaimsEntity:
    return CognitoClaimsEntity(
        sub=sub,
        client_id="web-client",
        token_use="access",
        provider=provider,
        email=email,
        name=name,
        email_verified=True,
    )


def _make_service() -> JitProvisionService:
    return JitProvisionService(
        link_repo=DjangoCognitoLinkRepository(),
        allowed_repo=DjangoUserAllowedEmailRepository(),
    )


class TestJitProvisionService:
    def test_returns_existing_user_when_link_exists(self) -> None:
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="existing", email="existing@example.com"
        )
        CognitoLink.objects.create(
            cognito_sub="sub-1",
            user=existing,
            provider="cognito",
            cognito_email="existing@example.com",
        )

        user = _make_service().provision(_make_claims(sub="sub-1", email="ignored@example.com"))

        assert user.pk == existing.pk
        # 既存リンクなのでテーブルに重複は作らない
        assert CognitoLink.objects.filter(cognito_sub="sub-1").count() == 1

    def test_links_existing_user_via_allowed_emails(self) -> None:
        """sub マッチがなくても、allowed_emails に登録された email なら既存 user に紐付ける。"""
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="akinori", email="akinori@example.com"
        )
        UserAllowedEmail.objects.create(user=existing, email="akinori@example.com")

        user = _make_service().provision(_make_claims(sub="new-sub", email="akinori@example.com"))

        assert user.pk == existing.pk
        link = CognitoLink.objects.get(cognito_sub="new-sub")
        assert link.user_id == existing.pk

    def test_raises_when_email_not_allowed(self) -> None:
        """allowed_emails に登録されていない email → reject (招待制)。"""
        # auth_user は存在しても、その email が allowed_emails に登録されていない場合は拒否
        user_model = get_user_model()
        user_model._default_manager.create(  # noqa: SLF001
            username="someone", email="someone@example.com"
        )
        service = _make_service()

        with pytest.raises(UserNotAllowedError, match="許可されていません"):
            service.provision(_make_claims(sub="brand-new", email="fresh@example.com"))

        assert CognitoLink.objects.filter(cognito_sub="brand-new").count() == 0

    def test_raises_when_claims_have_no_email(self) -> None:
        """email claim が無い JWT も拒否する。"""
        with pytest.raises(UserNotAllowedError, match="email claim"):
            _make_service().provision(_make_claims(sub="no-email", email=""))

    def test_links_via_allowed_emails_when_emails_differ_from_user_email(self) -> None:
        """auth_user.email と異なる email でも allowed に登録されていれば紐付け成功する (新仕様の核)。

        会社 email でアカウントを作った後、個人の Gmail を allowed に追加して
        Google ログインでも同じ auth_user にアクセスできる、というユースケース。
        """
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="akinori", email="akinori@sfass.net"
        )
        UserAllowedEmail.objects.create(user=existing, email="akinori@sfass.net")
        UserAllowedEmail.objects.create(user=existing, email="a.fukugi@gmail.com")

        # Google で別 email ログイン
        user = _make_service().provision(_make_claims(sub="google-sub", email="a.fukugi@gmail.com", provider="google"))

        assert user.pk == existing.pk
        link = CognitoLink.objects.get(cognito_sub="google-sub")
        assert link.user_id == existing.pk
        assert link.provider == "google"

    def test_multiple_links_per_user(self) -> None:
        """1 auth_user に複数の sub が紐付け可能 (ForeignKey 化の検証)。"""
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="multi", email="multi@example.com"
        )
        UserAllowedEmail.objects.create(user=existing, email="multi@example.com")
        UserAllowedEmail.objects.create(user=existing, email="other@example.com")
        service = _make_service()

        service.provision(_make_claims(sub="sub-a", email="multi@example.com", provider="cognito"))
        service.provision(_make_claims(sub="sub-b", email="other@example.com", provider="google"))

        assert CognitoLink.objects.filter(user_id=existing.pk).count() == 2

    def test_email_match_is_case_insensitive(self) -> None:
        """email の大文字小文字違いは同じユーザーとして扱う。"""
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="mixed", email="Mixed@Example.com"
        )
        UserAllowedEmail.objects.create(user=existing, email="Mixed@Example.com")

        user = _make_service().provision(_make_claims(sub="case-sub", email="mixed@example.com"))

        assert user.pk == existing.pk

    def test_records_provider_in_link(self) -> None:
        user_model = get_user_model()
        existing = user_model._default_manager.create(  # noqa: SLF001
            username="g_user", email="g@example.com"
        )
        UserAllowedEmail.objects.create(user=existing, email="g@example.com")

        _make_service().provision(_make_claims(sub="g-sub", email="g@example.com", provider="google"))

        link = CognitoLink.objects.get(cognito_sub="g-sub")
        assert link.provider == "google"
