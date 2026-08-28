"""GeminiClientService のレスポンス解析・生成設定のテスト（HTTP はモック）。"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.ai.application.services.gemini_client_service import (
    _MAX_OUTPUT_TOKENS,
    _THINKING_BUDGET,
    GeminiClientService,
    GeminiResponse,
)


def _mock_resp(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def _call(payload: dict[str, Any]) -> GeminiResponse:
    client = GeminiClientService(api_key="dummy", model="gemini-2.5-flash")
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.post.return_value = _mock_resp(payload)
        return client.chat("system", "user")


class TestGeminiClientServiceChat:
    def test_multiple_text_parts_are_concatenated(self) -> None:
        """thinking 有効時は parts が分割されうるため、全 text を連結する。"""
        result = _call(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "前半"}, {"text": "後半"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "thoughtsTokenCount": 300,
                },
            }
        )
        assert result.content == "前半後半"

    def test_non_text_part_is_skipped(self) -> None:
        """text を持たない part が混ざっても本文だけを取り出す。"""
        result = _call(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"functionCall": {}}, {"text": "本文"}]},
                        "finishReason": "STOP",
                    }
                ],
                "usageMetadata": {},
            }
        )
        assert result.content == "本文"

    def test_empty_body_raises(self) -> None:
        """thinking で出力枠を使い切り本文が空の場合はエラーにする。"""
        with pytest.raises(RuntimeError, match="本文が返りませんでした"):
            _call(
                {
                    "candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}],
                    "usageMetadata": {},
                }
            )

    def test_thinking_config_is_sent(self) -> None:
        """thinkingBudget を明示して dynamic thinking の暴走を防ぐ。"""
        client = GeminiClientService(api_key="dummy", model="gemini-2.5-flash")
        with patch("httpx.Client") as mock_client:
            post = mock_client.return_value.__enter__.return_value.post
            post.return_value = _mock_resp(
                {
                    "candidates": [{"content": {"parts": [{"text": "本文"}]}, "finishReason": "STOP"}],
                    "usageMetadata": {},
                }
            )
            client.chat("system", "user")

        generation_config = post.call_args.kwargs["json"]["generationConfig"]
        assert generation_config["thinkingConfig"] == {"thinkingBudget": _THINKING_BUDGET}
        assert generation_config["maxOutputTokens"] == _MAX_OUTPUT_TOKENS
