"""J-Quants クライアントの UL/LL フラグ取り込みテスト（純関数のみ）。"""

from __future__ import annotations

from apps.stocks.infrastructure.external.jquants_client import _to_bool_flag


class TestToBoolFlag:
    def test_string_one_is_true(self) -> None:
        assert _to_bool_flag("1") is True

    def test_string_zero_is_false(self) -> None:
        assert _to_bool_flag("0") is False

    def test_empty_is_false(self) -> None:
        assert _to_bool_flag("") is False

    def test_none_is_false(self) -> None:
        assert _to_bool_flag(None) is False

    def test_nan_is_false(self) -> None:
        assert _to_bool_flag("nan") is False

    def test_python_true_is_true(self) -> None:
        assert _to_bool_flag(True) is True

    def test_python_int_1_is_true(self) -> None:
        assert _to_bool_flag(1) is True

    def test_python_int_0_is_false(self) -> None:
        assert _to_bool_flag(0) is False
