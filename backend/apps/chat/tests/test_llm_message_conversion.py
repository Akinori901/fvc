"""LLM クライアントのメッセージ変換ロジックのテスト。

共通中間形式 → provider 固有形式の変換を検証する。
"""

from __future__ import annotations

import json

from apps.ai.application.services.gemini_client_service import _to_gemini_contents
from apps.ai.application.services.openai_client_service import _to_openai_messages
from apps.chat.domain.llm_client import ToolCall


class TestOpenAiMessageConversion:
    def test_user_message(self) -> None:
        result = _to_openai_messages([{"role": "user", "content": "こんにちは"}])
        assert result == [{"role": "user", "content": "こんにちは"}]

    def test_assistant_text_message(self) -> None:
        result = _to_openai_messages([{"role": "assistant", "content": "わかりました"}])
        assert result == [{"role": "assistant", "content": "わかりました"}]

    def test_assistant_with_tool_calls(self) -> None:
        result = _to_openai_messages(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [ToolCall(id="call_1", name="get_stock_summary", arguments={"code": "7203"})],
                }
            ]
        )
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["tool_calls"][0]["id"] == "call_1"
        assert result[0]["tool_calls"][0]["function"]["name"] == "get_stock_summary"
        # arguments は JSON 文字列で渡る
        assert json.loads(result[0]["tool_calls"][0]["function"]["arguments"]) == {"code": "7203"}

    def test_tool_result_message(self) -> None:
        result = _to_openai_messages([{"role": "tool", "tool_call_id": "call_1", "content": '{"price": 2500}'}])
        assert result == [{"role": "tool", "tool_call_id": "call_1", "content": '{"price": 2500}'}]

    def test_ignores_unknown_role(self) -> None:
        result = _to_openai_messages([{"role": "system", "content": "skip"}])
        assert result == []


class TestGeminiMessageConversion:
    def test_user_message(self) -> None:
        result = _to_gemini_contents([{"role": "user", "content": "こんにちは"}])
        assert result == [{"role": "user", "parts": [{"text": "こんにちは"}]}]

    def test_assistant_text_only(self) -> None:
        result = _to_gemini_contents([{"role": "assistant", "content": "わかりました"}])
        assert result == [{"role": "model", "parts": [{"text": "わかりました"}]}]

    def test_assistant_with_tool_calls(self) -> None:
        result = _to_gemini_contents(
            [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [ToolCall(id="g_1", name="get_stock_summary", arguments={"code": "7203"})],
                }
            ]
        )
        assert len(result) == 1
        assert result[0]["role"] == "model"
        assert result[0]["parts"][0]["functionCall"]["name"] == "get_stock_summary"
        assert result[0]["parts"][0]["functionCall"]["args"] == {"code": "7203"}

    def test_tool_result_parses_json_content(self) -> None:
        result = _to_gemini_contents(
            [
                {
                    "role": "tool",
                    "tool_call_id": "g_1",
                    "tool_name": "get_stock_summary",
                    "content": '{"price": 2500}',
                }
            ]
        )
        assert len(result) == 1
        # Gemini は functionResponse を user role の parts に入れる
        assert result[0]["role"] == "user"
        fr = result[0]["parts"][0]["functionResponse"]
        assert fr["name"] == "get_stock_summary"
        assert fr["response"] == {"price": 2500}

    def test_tool_result_wraps_non_dict_content(self) -> None:
        """文字列リテラルは {result: ...} でラップされる。"""
        result = _to_gemini_contents(
            [
                {
                    "role": "tool",
                    "tool_call_id": "g_2",
                    "tool_name": "search_stock_news_sources",
                    "content": "not a json",
                }
            ]
        )
        fr = result[0]["parts"][0]["functionResponse"]
        assert fr["response"] == {"result": "not a json"}
