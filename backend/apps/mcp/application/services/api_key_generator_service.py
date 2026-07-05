"""API キー生成 + bcrypt ハッシュサービス。

キー形式: `fvc_mcp_<32文字英数記号>`（合計 40 文字）
DB に保存するもの:
- `key_prefix`: 先頭 8 文字（識別表示・検索用）
- `key_hash`: bcrypt(plain_key)
"""

from __future__ import annotations

import secrets

import bcrypt

from ...domain.entities import API_KEY_PREFIX_LENGTH, API_KEY_PREFIX_LITERAL

_RANDOM_LENGTH = 32


class ApiKeyGeneratorService:
    """API キー生成 + 検証。"""

    def generate(self) -> tuple[str, str, str]:
        """平文キー / key_prefix / key_hash の 3 つを返す。

        Returns:
            (plain_key, key_prefix, key_hash)
        """
        random_part = secrets.token_urlsafe(_RANDOM_LENGTH)[:_RANDOM_LENGTH]
        plain_key = f"{API_KEY_PREFIX_LITERAL}{random_part}"
        key_prefix = plain_key[:API_KEY_PREFIX_LENGTH]
        key_hash = bcrypt.hashpw(plain_key.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
        return plain_key, key_prefix, key_hash

    def verify(self, plain_key: str, key_hash: str) -> bool:
        """平文キーと bcrypt ハッシュを比較。"""
        if not plain_key or not key_hash:
            return False
        try:
            return bcrypt.checkpw(plain_key.encode("utf-8"), key_hash.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def extract_prefix(plain_key: str) -> str:
        """平文キーから DB 検索用の prefix を取り出す。"""
        return plain_key[:API_KEY_PREFIX_LENGTH]
