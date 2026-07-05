from dataclasses import dataclass

from apps.core.exceptions import ValidationError


@dataclass(frozen=True)
class StockCode:
    """証券コード値オブジェクト"""

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("証券コードは必須です")
        if len(self.value) > 10:
            raise ValidationError("証券コードは10文字以内で入力してください")


@dataclass(frozen=True)
class FiscalYear:
    """会計年度値オブジェクト"""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1900 or self.value > 2100:
            raise ValidationError(f"会計年度が不正です: {self.value}")
