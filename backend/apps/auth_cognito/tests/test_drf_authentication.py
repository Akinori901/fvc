"""CognitoJWTAuthentication のテスト。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.auth_cognito.domain.entities import CognitoClaimsEntity
from apps.auth_cognito.domain.exceptions import InvalidCognitoTokenError
from apps.auth_cognito.presentation.drf_authentication import CognitoJWTAuthentication

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper

    from .conftest import SigningKeyPair


_COGNITO_ISSUER = "https://cognito-idp.ap-northeast-1.amazonaws.com/pool"


def _build_request(token: str | None = None) -> Request:
    factory = APIRequestFactory()
    if token is not None:
        django_request = factory.get("/api/test/", HTTP_AUTHORIZATION=f"Bearer {token}")
    else:
        django_request = factory.get("/api/test/")
    return Request(django_request)


def _bypass_issuer_check() -> Any:
    """`_looks_like_cognito_token` を常に True にする patch context.

    Cognito JWT 経路を通すテストで使う。実体の iss 判定は別テストで検証する。
    """
    return patch.object(CognitoJWTAuthentication, "_looks_like_cognito_token", return_value=True)


class TestCognitoJWTAuthenticationHeaderParsing:
    def test_returns_none_when_no_authorization_header(self) -> None:
        auth = CognitoJWTAuthentication()
        request = _build_request(token=None)
        assert auth.authenticate(request) is None

    def test_returns_none_for_mcp_api_key_prefix(self) -> None:
        """fvc_mcp_ で始まる Bearer は MCP 認証クラスに委ねる。"""
        auth = CognitoJWTAuthentication()
        request = _build_request(token="fvc_mcp_secret_value")
        # config.container を一切呼ばずに None を返すこと
        with patch("config.container.cognito_jwt_verifier_service") as mocked:
            assert auth.authenticate(request) is None
            mocked.assert_not_called()

    def test_returns_none_for_non_bearer_scheme(self) -> None:
        auth = CognitoJWTAuthentication()
        factory = APIRequestFactory()
        django_request = factory.get("/api/test/", HTTP_AUTHORIZATION="Basic xxx")
        request = Request(django_request)
        assert auth.authenticate(request) is None

    def test_returns_none_for_empty_bearer(self) -> None:
        auth = CognitoJWTAuthentication()
        request = _build_request(token="")
        assert auth.authenticate(request) is None


@pytest.mark.django_db
class TestCognitoJWTAuthenticationFlow:
    def test_invalid_token_raises_authentication_failed(self) -> None:
        auth = CognitoJWTAuthentication()
        request = _build_request(token="cognito.jwt.token")

        verifier = MagicMock()
        verifier.verify.side_effect = InvalidCognitoTokenError("bad signature")

        with (
            _bypass_issuer_check(),
            patch("config.container.cognito_jwt_verifier_service", return_value=verifier),
            pytest.raises(AuthenticationFailed, match="Invalid Cognito token"),
        ):
            auth.authenticate(request)

    def test_successful_authentication_returns_user_and_token(self) -> None:
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="alice", email="alice@example.com", is_active=True
        )

        claims = CognitoClaimsEntity(
            sub="alice-sub",
            client_id="web-client",
            token_use="access",
            provider="cognito",
            email="alice@example.com",
        )

        verifier = MagicMock()
        verifier.verify.return_value = claims

        provision = MagicMock()
        provision.provision.return_value = user

        link_repo = MagicMock()
        link_repo.find_by_sub.return_value = None  # touch をスキップ

        auth = CognitoJWTAuthentication()
        request = _build_request(token="cognito.jwt.token")

        with (
            _bypass_issuer_check(),
            patch.multiple(
                "config.container",
                cognito_jwt_verifier_service=lambda: verifier,
                jit_provision_service=lambda: provision,
                cognito_link_repository=lambda: link_repo,
            ),
        ):
            result = auth.authenticate(request)

        assert result is not None
        authenticated_user, token = result
        assert authenticated_user.pk == user.pk
        assert token == "cognito.jwt.token"
        verifier.verify.assert_called_once_with("cognito.jwt.token")

    def test_inactive_user_is_rejected(self) -> None:
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="disabled", email="disabled@example.com", is_active=False
        )

        claims = CognitoClaimsEntity(sub="disabled-sub", client_id="web-client", token_use="access", provider="cognito")

        verifier = MagicMock()
        verifier.verify.return_value = claims
        provision = MagicMock()
        provision.provision.return_value = user
        link_repo = MagicMock()
        link_repo.find_by_sub.return_value = None

        auth = CognitoJWTAuthentication()
        request = _build_request(token="cognito.jwt.token")

        with (
            _bypass_issuer_check(),
            patch.multiple(
                "config.container",
                cognito_jwt_verifier_service=lambda: verifier,
                jit_provision_service=lambda: provision,
                cognito_link_repository=lambda: link_repo,
            ),
            pytest.raises(AuthenticationFailed, match="disabled"),
        ):
            auth.authenticate(request)

    def test_touches_last_signed_in_when_link_exists(self) -> None:
        user_model = get_user_model()
        user = user_model._default_manager.create(  # noqa: SLF001
            username="bob", email="bob@example.com", is_active=True
        )

        claims = CognitoClaimsEntity(sub="bob-sub", client_id="web-client", token_use="access", provider="cognito")

        verifier = MagicMock()
        verifier.verify.return_value = claims
        provision = MagicMock()
        provision.provision.return_value = user

        # link が存在するシナリオ
        link = MagicMock()
        link.id = 42
        link_repo = MagicMock()
        link_repo.find_by_sub.return_value = link

        auth = CognitoJWTAuthentication()
        request = _build_request(token="cognito.jwt.token")

        with (
            _bypass_issuer_check(),
            patch.multiple(
                "config.container",
                cognito_jwt_verifier_service=lambda: verifier,
                jit_provision_service=lambda: provision,
                cognito_link_repository=lambda: link_repo,
            ),
        ):
            auth.authenticate(request)

        link_repo.touch_last_signed_in.assert_called_once_with(42)


class TestCognitoJWTAuthenticationFallback:
    """non-Cognito JWT を None で素通りさせるフォールバック判定。

    2026-05-22 障害 (PR #54/#55 で復旧) の根本対応。詳細は
    `incident_cognito_phase_b_2026_05_22.md` を参照。
    """

    def _make_jwt(self, *, issuer: str, exp_seconds: int = 3600) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": "u1",
            "iss": issuer,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=exp_seconds)).timestamp()),
        }
        # 署名は適当 (検証されないので OK)。kid もテスト用に付与。
        return jwt.encode(payload, "test-secret", algorithm="HS256", headers={"kid": "test-kid"})

    def test_returns_none_for_simple_jwt_token_with_different_issuer(self, settings: SettingsWrapper) -> None:
        """SimpleJWT が発行した token (iss が Cognito issuer と一致しない) は None。

        これが本番障害 (PR #53 後の 401) の根本原因に対するレグレッションテスト。
        """
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        token = self._make_jwt(issuer="some-other-issuer")  # SimpleJWT 想定
        auth = CognitoJWTAuthentication()
        request = _build_request(token=token)

        # verify が呼ばれず None が返ること
        with patch("config.container.cognito_jwt_verifier_service") as mocked:
            assert auth.authenticate(request) is None
            mocked.assert_not_called()

    def test_returns_none_when_issuer_not_configured(self, settings: SettingsWrapper) -> None:
        """COGNITO_JWT_ISSUER 未設定環境では常にフォールバック。"""
        settings.COGNITO_JWT_ISSUER = ""
        token = self._make_jwt(issuer=_COGNITO_ISSUER)
        auth = CognitoJWTAuthentication()
        request = _build_request(token=token)

        with patch("config.container.cognito_jwt_verifier_service") as mocked:
            assert auth.authenticate(request) is None
            mocked.assert_not_called()

    def test_returns_none_for_non_jwt_token(self, settings: SettingsWrapper) -> None:
        """JWT として decode 不能な文字列 (random opaque token 等) は None。"""
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        auth = CognitoJWTAuthentication()
        request = _build_request(token="totally.not.a.jwt")

        with patch("config.container.cognito_jwt_verifier_service") as mocked:
            assert auth.authenticate(request) is None
            mocked.assert_not_called()

    def test_returns_none_when_iss_claim_missing(self, settings: SettingsWrapper) -> None:
        """iss claim が無い JWT (異常系) は None。"""
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        # iss を入れずに encode
        token = jwt.encode({"sub": "x"}, "k", algorithm="HS256", headers={"kid": "k"})
        auth = CognitoJWTAuthentication()
        request = _build_request(token=token)

        with patch("config.container.cognito_jwt_verifier_service") as mocked:
            assert auth.authenticate(request) is None
            mocked.assert_not_called()

    def test_invokes_verifier_when_iss_matches_cognito_issuer(self, settings: SettingsWrapper) -> None:
        """iss が Cognito issuer と一致したら verify が呼ばれる。"""
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        token = self._make_jwt(issuer=_COGNITO_ISSUER)

        # verify は失敗させて、確実に「呼ばれた」ことを assert する
        verifier = MagicMock()
        verifier.verify.side_effect = InvalidCognitoTokenError("simulated")

        auth = CognitoJWTAuthentication()
        request = _build_request(token=token)

        with (
            patch("config.container.cognito_jwt_verifier_service", return_value=verifier),
            pytest.raises(AuthenticationFailed),
        ):
            auth.authenticate(request)
        verifier.verify.assert_called_once_with(token)


@pytest.mark.django_db
class TestLooksLikeCognitoTokenIntegration:
    """`_looks_like_cognito_token` を実装レベルで確認するテスト (peek のみ)。"""

    def test_returns_true_for_real_cognito_signed_token(
        self, signing_key: SigningKeyPair, settings: SettingsWrapper
    ) -> None:
        """conftest の signing_key で署名された Cognito 風 token は True。"""
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        token = signing_key.issue(issuer=_COGNITO_ISSUER, client_id="web-client")
        assert CognitoJWTAuthentication._looks_like_cognito_token(token) is True

    def test_returns_false_for_different_issuer(self, signing_key: SigningKeyPair, settings: SettingsWrapper) -> None:
        settings.COGNITO_JWT_ISSUER = _COGNITO_ISSUER
        token = signing_key.issue(issuer="https://other-idp.example.com/", client_id="web-client")
        assert CognitoJWTAuthentication._looks_like_cognito_token(token) is False


class TestAuthenticateHeader:
    def test_returns_bearer_realm(self) -> None:
        auth = CognitoJWTAuthentication()
        request = _build_request(token=None)
        assert auth.authenticate_header(request) == 'Bearer realm="cognito"'
