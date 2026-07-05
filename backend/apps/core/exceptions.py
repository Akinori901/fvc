class DomainError(Exception):
    """ドメイン層のビジネスルール違反"""


class EntityNotFoundError(DomainError):
    """エンティティが見つからない"""


class ValidationError(DomainError):
    """ドメインバリデーションエラー"""
