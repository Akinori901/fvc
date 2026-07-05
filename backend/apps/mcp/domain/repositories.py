"""MCP / 外部AI連携 リポジトリインターフェース。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import McpApiKeyEntity


class McpApiKeyRepository(ABC):
    """MCP API キーリポジトリ。"""

    @abstractmethod
    def save(self, entity: McpApiKeyEntity) -> McpApiKeyEntity: ...

    @abstractmethod
    def find_by_id(self, key_id: int) -> McpApiKeyEntity | None: ...

    @abstractmethod
    def find_active_by_prefix(self, key_prefix: str) -> list[McpApiKeyEntity]:
        """key_prefix（先頭8文字）で前方マッチ。bcrypt 検証は呼び出し側で行う。"""

    @abstractmethod
    def find_by_user(self, user_id: int) -> list[McpApiKeyEntity]: ...

    @abstractmethod
    def revoke(self, key_id: int, user_id: int) -> bool:
        """is_active=False に更新。失敗時は False。"""

    @abstractmethod
    def update_last_used(self, key_id: int) -> None: ...
