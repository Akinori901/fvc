"""管理者による auth_user 新規作成サービス。

Cognito ログインのみを想定するためパスワードは設定しない (unusable password)。
allowed_emails への追加は UseCase 層でオーケストレーションする。
"""

from __future__ import annotations

from django.contrib.auth import get_user_model

from apps.auth_cognito.application.dto import AdminUserRow


class AdminUserCreateService:
    """email から auth_user を作成する (重複時は ValueError)。"""

    def create_user(self, email: str) -> AdminUserRow:
        email_norm = email.strip().lower()
        if not email_norm:
            msg = "email は必須です"
            raise ValueError(msg)

        user_model = get_user_model()
        # email でも username でも重複チェック (username = email の運用なので両方ヒットしうる)
        if user_model._default_manager.filter(email__iexact=email_norm).exists():  # noqa: SLF001
            msg = f"email {email_norm} は既に登録されています"
            raise ValueError(msg)
        if user_model._default_manager.filter(username=email_norm).exists():  # noqa: SLF001
            msg = f"username {email_norm} は既に使用されています"
            raise ValueError(msg)

        user = user_model._default_manager.create(  # noqa: SLF001
            username=email_norm,
            email=email_norm,
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])

        return AdminUserRow(
            id=user.pk,
            email=user.email,
            username=user.username,
            is_superuser=bool(user.is_superuser),
            is_staff=bool(user.is_staff),
            is_active=bool(user.is_active),
            date_joined=user.date_joined,
            last_login=user.last_login,
            cognito_links=[],
            allowed_emails=[],
        )
