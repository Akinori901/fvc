"""management_handler のタイムアウト制御テスト（DB 不要・subprocess をフェイク化）。

従来は全コマンド一律 timeout=870（Lambda 上限 900 の直前）で、異常時に上限まで
張り付いて GB 秒を浪費していた。既定を実測ベースに下げ、重いコマンドのみ個別に
延長する形に変えたため、その分岐と打ち切り時の戻り値を守るテスト。
あわせて、打ち切りが CloudWatch に残るためのログ設定も守る。
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any

import pytest

from config.management_handler import (
    COMMAND_TIMEOUTS,
    DEFAULT_COMMAND_TIMEOUT,
    _configure_logging,
    handler,
)


class _CompletedStub:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdout = "done"
        self.stderr = ""


@pytest.fixture
def captured_timeout(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """subprocess.run に渡された timeout を記録するフェイク。"""
    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> _CompletedStub:
        captured["cmd"] = cmd
        captured["timeout"] = kwargs.get("timeout")
        return _CompletedStub()

    monkeypatch.setattr(subprocess, "run", fake_run)
    return captured


class TestCommandTimeout:
    def test_scheduled_command_uses_default_timeout(self, captured_timeout: dict[str, Any]) -> None:
        """定期実行コマンドは既定タイムアウトで打ち切られる。"""
        result = handler({"command": "generate_recommendations"}, None)

        assert captured_timeout["timeout"] == DEFAULT_COMMAND_TIMEOUT
        assert result["statusCode"] == 0

    def test_heavy_command_uses_extended_timeout(self, captured_timeout: dict[str, Any]) -> None:
        """既定値では足りないコマンドは個別指定で延長される。"""
        handler({"command": "sync_news", "args": ["--category", "stock"]}, None)

        assert captured_timeout["timeout"] == COMMAND_TIMEOUTS["sync_news"]
        assert captured_timeout["timeout"] > DEFAULT_COMMAND_TIMEOUT

    def test_timeouts_stay_within_lambda_limit(self) -> None:
        """個別指定を含め Lambda の実行上限を超えない。"""
        # Lambda 側 timeout は 900 秒。後片付けの余地を残す。
        assert all(v <= 870 for v in COMMAND_TIMEOUTS.values())
        assert DEFAULT_COMMAND_TIMEOUT <= 870

    def test_args_are_passed_to_management_command(self, captured_timeout: dict[str, Any]) -> None:
        """イベントの args が管理コマンドへそのまま渡る。"""
        handler({"command": "sync_prices", "args": ["--market", "JP"]}, None)

        assert captured_timeout["cmd"][-3:] == ["sync_prices", "--market", "JP"]


class TestTimeoutExpired:
    def test_timeout_returns_result_instead_of_raising(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打ち切りを未処理例外にせず、原因の分かる結果として返す。"""

        def fake_run(cmd: list[str], **kwargs: Any) -> None:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"], output="partial", stderr="boom")

        monkeypatch.setattr(subprocess, "run", fake_run)

        result = handler({"command": "generate_recommendations"}, None)

        assert result["statusCode"] == 1
        assert result["timedOut"] is True
        assert result["timeout"] == DEFAULT_COMMAND_TIMEOUT
        assert result["returncode"] is None
        assert "boom" in result["stderr"]

    def test_timeout_decodes_bytes_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打ち切り時の出力が bytes でも文字列で返す。"""

        def fake_run(cmd: list[str], **kwargs: Any) -> None:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"], output=b"out", stderr=b"err")

        monkeypatch.setattr(subprocess, "run", fake_run)

        result = handler({"command": "generate_recommendations"}, None)

        assert result["stdout"] == "out"
        assert result["stderr"] == "err"

    def test_timeout_handles_missing_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """打ち切り時に出力が None でも落ちない。"""

        def fake_run(cmd: list[str], **kwargs: Any) -> None:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs["timeout"])

        monkeypatch.setattr(subprocess, "run", fake_run)

        result = handler({"command": "generate_recommendations"}, None)

        assert result["stdout"] == ""
        assert result["stderr"] == ""
        assert result["timedOut"] is True


class TestCommandValidation:
    def test_missing_command_returns_400(self) -> None:
        """command 未指定は 400 を返す。"""
        assert handler({}, None)["statusCode"] == 400


class TestLoggingIsConfigured:
    """settings の LOGGING はこのハンドラに効かない（django.setup() を通らない）。

    Lambda ランタイムが先に root logger へハンドラを付けるため、force=True で
    貼り直さないと打ち切りや失敗が CloudWatch に何も残らない。
    """

    def test_handler_configures_logging(
        self, monkeypatch: pytest.MonkeyPatch, captured_timeout: dict[str, Any]
    ) -> None:
        called: dict[str, Any] = {}

        def fake_basic_config(**kwargs: Any) -> None:
            called.update(kwargs)

        monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

        handler({"command": "generate_recommendations"}, None)

        assert called.get("force") is True, "force=True でないと Lambda の既定ハンドラに勝てない"
        assert called.get("level") == logging.INFO

    def test_logging_config_emits_records(self, capsys: pytest.CaptureFixture[str]) -> None:
        """設定後、INFO が実際に stderr（Lambda では CloudWatch）へ出る。

        force=True は pytest の caplog ハンドラごと貼り直すため、
        caplog ではなく実際の出力先で検証する。
        """
        _configure_logging()

        logging.getLogger("config.management_handler").info("hello-from-handler")

        assert "hello-from-handler" in capsys.readouterr().err
