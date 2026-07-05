"""OpenAI Chat Completions API 呼び出しサービス。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from apps.ai.domain.exceptions import AiApiKeyInvalidError
from apps.chat.domain.llm_client import AbstractLlmClient, LlmResponse, ToolCall


@dataclass
class OpenAiResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class OpenAiClientService(AbstractLlmClient):
    """OpenAI API を httpx で直接呼び出す（openai SDK は導入しない）。

    既存の `chat()` メソッドは apps/ai/AnalyzeStockUseCase 用に維持しつつ、
    apps/chat の Function Calling ループ用に `chat_with_tools()` を追加する。
    """

    _BASE_URL = "https://api.openai.com/v1/chat/completions"
    _TIMEOUT = 60.0  # 個別株 AI 分析 (chat) 用
    _TIMEOUT_TOOLS = 40.0  # Function Calling 用 (Lambda 60s timeout の余裕)

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def chat(self, system_prompt: str, user_prompt: str) -> OpenAiResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 1500,
        }
        try:
            with httpx.Client(timeout=self._TIMEOUT) as client:
                resp = client.post(self._BASE_URL, json=payload, headers=headers)

            if resp.status_code == 401:
                raise AiApiKeyInvalidError("OpenAI APIキーが無効です。設定ページで正しいAPIキーを登録してください。")
            resp.raise_for_status()

            data = resp.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})
            return OpenAiResponse(
                content=choice["message"]["content"],
                model=data["model"],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
        except AiApiKeyInvalidError:
            raise
        except httpx.TimeoutException as e:
            raise TimeoutError("OpenAI APIがタイムアウトしました（60秒）") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenAI APIエラー: {e.response.status_code}") from e

    def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        """Function Calling 対応の Chat Completions 呼び出し。

        messages は共通中間形式（role / content / tool_call_id / tool_calls）。
        本メソッド内で OpenAI 固有形式に変換する。
        """
        openai_messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(_to_openai_messages(messages))

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self._TIMEOUT_TOOLS) as client:
                resp = client.post(self._BASE_URL, json=payload, headers=headers)

            if resp.status_code == 401:
                raise AiApiKeyInvalidError("OpenAI APIキーが無効です。設定ページで正しいAPIキーを登録してください。")
            resp.raise_for_status()

            data = resp.json()
            choice = data["choices"][0]
            msg = choice["message"]
            usage = data.get("usage", {})

            tool_calls: list[ToolCall] = []
            for call in msg.get("tool_calls") or []:
                fn = call.get("function", {})
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(id=call.get("id", ""), name=fn.get("name", ""), arguments=args))

            return LlmResponse(
                content=msg.get("content") or "",
                model=data.get("model", self._model),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                tool_calls=tool_calls,
            )
        except AiApiKeyInvalidError:
            raise
        except httpx.TimeoutException as e:
            raise TimeoutError("OpenAI APIがタイムアウトしました（40秒）") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"OpenAI APIエラー: {e.response.status_code}") from e


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """共通中間形式 → OpenAI 形式に変換。

    入力 (共通中間形式):
      - {"role": "user", "content": "..."}
      - {"role": "assistant", "content": "...", "tool_calls": [ToolCall, ...]}
      - {"role": "tool", "tool_call_id": "...", "content": "..."}
    """
    result: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "user":
            result.append({"role": "user", "content": m.get("content", "")})
        elif role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.get("content") or ""}
            tool_calls = m.get("tool_calls") or []
            if tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in tool_calls
                ]
            result.append(entry)
        elif role == "tool":
            result.append(
                {
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id", ""),
                    "content": m.get("content", ""),
                }
            )
    return result
