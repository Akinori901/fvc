"""set_api_key 管理コマンドのテスト。"""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.stocks.models import ApiConfig


@pytest.mark.django_db
class TestSetApiKeyCommand:
    def test_creates_new_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FVC_API_KEY", "test-key-12345")
        call_command("set_api_key", "--provider", "edinet")

        config = ApiConfig.objects.get(provider="edinet")
        assert config.api_key == "test-key-12345"
        assert config.is_enabled is True

    def test_updates_existing_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        ApiConfig.objects.create(provider="edinet", api_key="old-key", is_enabled=False)

        monkeypatch.setenv("FVC_API_KEY", "new-key")
        call_command("set_api_key", "--provider", "edinet")

        # 重複行を作らず既存行を更新する
        assert ApiConfig.objects.filter(provider="edinet").count() == 1
        config = ApiConfig.objects.get(provider="edinet")
        assert config.api_key == "new-key"
        assert config.is_enabled is True

    def test_disable_flag_sets_is_enabled_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FVC_API_KEY", "test-key")
        call_command("set_api_key", "--provider", "edinet", "--disable")

        assert ApiConfig.objects.get(provider="edinet").is_enabled is False

    def test_missing_env_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FVC_API_KEY", raising=False)
        with pytest.raises(CommandError, match="FVC_API_KEY"):
            call_command("set_api_key", "--provider", "edinet")

    def test_blank_env_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 空白のみのキーは未設定として扱う
        monkeypatch.setenv("FVC_API_KEY", "   ")
        with pytest.raises(CommandError, match="FVC_API_KEY"):
            call_command("set_api_key", "--provider", "edinet")

    def test_api_key_is_not_printed(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        # ログ露出を避けるため、キー本体は出力しない
        secret = "super-secret-key-value"
        monkeypatch.setenv("FVC_API_KEY", secret)
        call_command("set_api_key", "--provider", "edinet")

        assert secret not in capsys.readouterr().out
