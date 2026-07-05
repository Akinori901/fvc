"""ChatOrchestrationService のテスト。

LLM クライアントと ToolInvocationService をモック化し、Function Calling
ループの動作を検証する:
1. ツール呼び出しなしの即時応答
2. ツール呼び出し 1 回 → 最終応答
3. MAX_ITER 到達時の打ち切り
4. ツール実行失敗時のエラーメッセージ込みで継続
5. 認可エラー (PermissionError) の扱い
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.chat.application.services.chat_orchestration_service import (
    ChatOrchestrationService,
)
from apps.chat.domain.entities import ChatMessageEntity
from apps.chat.domain.llm_client import AbstractLlmClient, LlmResponse, ToolCall


class _FakeLlmClient(AbstractLlmClient):
    """事前に並べた応答を順に返すモッククライアント。"""

    def __init__(self, responses: list[LlmResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        self.calls.append({"system_prompt": system_prompt, "messages": list(messages), "tools": tools})
        if not self._responses:
            raise AssertionError("FakeLlmClient: 想定回数を超えて呼ばれた")
        return self._responses.pop(0)


class _FakeToolInvocationService:
    """ツール呼び出しの結果を事前に登録できるモック。

    behavior に Exception を入れると raise する。
    """

    def __init__(self, behaviors: dict[str, Any]) -> None:
        self._behaviors = behaviors
        self.calls: list[dict[str, Any]] = []

    def invoke(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"tool_name": tool_name, "params": params, "user_id": user_id})
        result = self._behaviors[tool_name]
        if isinstance(result, Exception):
            raise result
        assert isinstance(result, dict)
        return result


def _llm_text(content: str, *, prompt_tokens: int = 10, completion_tokens: int = 5) -> LlmResponse:
    return LlmResponse(
        content=content,
        model="test-model",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def _llm_tool_call(name: str, arguments: dict[str, Any], *, call_id: str = "call_1") -> LlmResponse:
    return LlmResponse(
        content="",
        model="test-model",
        prompt_tokens=10,
        completion_tokens=5,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
    )


class TestChatOrchestrationServiceNoToolCalls:
    def test_immediate_text_response(self) -> None:
        service = ChatOrchestrationService()
        llm = _FakeLlmClient([_llm_text("わかりました")])
        tool_svc = _FakeToolInvocationService({})

        result = service.run(
            session_id=1,
            provider="gemini",
            model="gemini-2.5-flash",
            system_prompt="sys",
            previous_messages=[],
            user_message="こんにちは",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        # user + assistant の 2 件のみ生成
        assert len(result.new_messages) == 2
        assert result.new_messages[0].role == "user"
        assert result.new_messages[0].content == "こんにちは"
        assert result.new_messages[1].role == "assistant"
        assert result.new_messages[1].content == "わかりました"
        assert result.final_assistant_content == "わかりました"
        assert result.iterations == 1
        assert result.truncated is False
        assert result.total_prompt_tokens == 10
        assert result.total_completion_tokens == 5


class TestChatOrchestrationServiceSingleToolCall:
    def test_one_tool_call_then_final_answer(self) -> None:
        service = ChatOrchestrationService()
        llm = _FakeLlmClient(
            [
                _llm_tool_call("get_stock_summary", {"code": "7203"}, call_id="c1"),
                _llm_text("トヨタの株価は2500円です"),
            ]
        )
        tool_svc = _FakeToolInvocationService({"get_stock_summary": {"code": "7203", "price": 2500}})

        result = service.run(
            session_id=10,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=[],
            user_message="7203の状況は？",
            llm_client=llm,
            tools=[{"type": "function", "function": {"name": "get_stock_summary"}}],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        # user + assistant(tool_call) + tool(result) + assistant(final) の 4 件
        roles = [m.role for m in result.new_messages]
        assert roles == ["user", "assistant", "tool", "assistant"]
        assert result.new_messages[2].tool_name == "get_stock_summary"
        assert result.new_messages[2].tool_result == {"code": "7203", "price": 2500}
        assert result.final_assistant_content == "トヨタの株価は2500円です"
        assert result.iterations == 2
        assert result.truncated is False
        # ToolInvocationService が user_id 付きで呼ばれた
        assert tool_svc.calls[0]["user_id"] == 42
        assert tool_svc.calls[0]["params"] == {"code": "7203"}


class TestChatOrchestrationServiceMaxIter:
    def test_max_iter_truncates(self) -> None:
        """MAX_ITER=2 で永遠にツール呼び出しを続ける場合、打ち切られる。"""
        service = ChatOrchestrationService(max_iter=2)
        # 毎回ツール呼び出しを返す LLM
        llm = _FakeLlmClient(
            [
                _llm_tool_call("get_stock_summary", {"code": "7203"}, call_id="c1"),
                _llm_tool_call("get_stock_summary", {"code": "7203"}, call_id="c2"),
            ]
        )
        tool_svc = _FakeToolInvocationService({"get_stock_summary": {"price": 100}})

        result = service.run(
            session_id=20,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=[],
            user_message="調べて",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        assert result.truncated is True
        assert result.iterations == 2
        assert "打ち切り" in result.final_assistant_content


class TestChatOrchestrationServiceToolFailure:
    def test_tool_exception_is_swallowed_and_continues(self) -> None:
        """ツール例外時はエラーメッセージを tool result に入れてループ継続。"""
        service = ChatOrchestrationService()
        llm = _FakeLlmClient(
            [
                _llm_tool_call("get_stock_summary", {"code": "9999"}),
                _llm_text("該当銘柄が見つかりませんでした"),
            ]
        )
        tool_svc = _FakeToolInvocationService({"get_stock_summary": ValueError("銘柄が見つかりません: 9999")})

        result = service.run(
            session_id=30,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=[],
            user_message="9999は？",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        tool_msg = next(m for m in result.new_messages if m.role == "tool")
        assert "エラー" in tool_msg.content
        assert "9999" in tool_msg.content
        assert result.final_assistant_content == "該当銘柄が見つかりませんでした"

    def test_permission_error_is_captured_with_friendly_message(self) -> None:
        service = ChatOrchestrationService()
        llm = _FakeLlmClient(
            [
                _llm_tool_call("get_my_holdings", {}),
                _llm_text("認証情報がありません"),
            ]
        )
        tool_svc = _FakeToolInvocationService({"get_my_holdings": PermissionError("認証が必要です")})

        result = service.run(
            session_id=40,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=[],
            user_message="保有は？",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=None,
        )

        tool_msg = next(m for m in result.new_messages if m.role == "tool")
        assert "認証が必要" in tool_msg.content


class TestChatOrchestrationServicePreviousMessages:
    def test_previous_messages_are_sent_to_llm(self) -> None:
        """既存セッション継続時、過去メッセージが LLM 呼び出しに含まれる。"""
        service = ChatOrchestrationService()
        llm = _FakeLlmClient([_llm_text("続きの応答")])
        tool_svc = _FakeToolInvocationService({})
        previous = [
            ChatMessageEntity(session_id=50, role="user", content="前回の質問"),
            ChatMessageEntity(session_id=50, role="assistant", content="前回の応答"),
        ]

        service.run(
            session_id=50,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=previous,
            user_message="続きを",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        # 過去 2 件 + 今回の user メッセージで合計 3 件
        sent_messages = llm.calls[0]["messages"]
        assert len(sent_messages) == 3
        assert sent_messages[0]["content"] == "前回の質問"
        assert sent_messages[1]["content"] == "前回の応答"
        assert sent_messages[2]["content"] == "続きを"


class TestChatOrchestrationServiceEmptyTools:
    def test_empty_tools_passes_none_to_llm(self) -> None:
        """tools=[] のときは LLM に tools=None を渡す（プレーンチャット）。"""
        service = ChatOrchestrationService()
        llm = _FakeLlmClient([_llm_text("はい")])
        tool_svc = _FakeToolInvocationService({})

        service.run(
            session_id=60,
            provider="openai",
            model="gpt-4o-mini",
            system_prompt="sys",
            previous_messages=[],
            user_message="hi",
            llm_client=llm,
            tools=[],
            tool_invocation_service=tool_svc,  # type: ignore[arg-type]
            user_id=42,
        )

        assert llm.calls[0]["tools"] is None


@pytest.fixture
def basic_service() -> ChatOrchestrationService:
    return ChatOrchestrationService()
