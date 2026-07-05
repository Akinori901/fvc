"""API キー認証ユースケース。

Bearer トークン（平文 API キー）→ Django User を解決する。
プレフィックス（先頭 8 文字）で DB 検索 → 候補に対して bcrypt 検証 →
ヒットしたら is_active 確認 + last_used_at 更新 + user 返却。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from ...domain.repositories import McpApiKeyRepository
    from ..services.api_key_generator_service import ApiKeyGeneratorService


class AuthenticateApiKeyUseCase:
    """API キーで認証する。"""

    def __init__(
        self,
        api_key_repo: McpApiKeyRepository,
        generator: ApiKeyGeneratorService,
    ) -> None:
        self._api_key_repo = api_key_repo
        self._generator = generator

    def execute(self, plain_key: str) -> Any | None:
        """Returns Django user or None."""
        if not plain_key:
            return None

        key_prefix = self._generator.extract_prefix(plain_key)
        candidates = self._api_key_repo.find_active_by_prefix(key_prefix)
        if not candidates:
            return None

        for entity in candidates:
            if not self._generator.verify(plain_key, entity.key_hash):
                continue
            if not entity.is_active or entity.id is None:
                continue

            self._api_key_repo.update_last_used(entity.id)
            user_model = get_user_model()
            user = user_model.objects.filter(pk=entity.user_id).first()
            return user

        return None
