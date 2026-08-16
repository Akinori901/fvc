"""Google Gemini API 呼び出しサービス。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from apps.ai.domain.exceptions import AiApiKeyInvalidError
from apps.chat.domain.llm_client import AbstractLlmClient, LlmResponse, ToolCall

logger = logging.getLogger(__name__)

# httpx のデフォルトログが URL（APIキー含む）を出力するのを防止
logging.getLogger("httpx").setLevel(logging.WARNING)

_MAX_RETRIES = 2
_BASE_DELAY = 3  # seconds


@dataclass
class GeminiResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class GeminiClientService(AbstractLlmClient):
    """Gemini API を httpx で直接呼び出す。

    既存の `chat()` メソッドは apps/ai/AnalyzeStockUseCase 用に維持しつつ、
    apps/chat の Function Calling ループ用に `chat_with_tools()` を追加する。
    """

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    # 個別株 AI 分析 (chat) 用。API Gateway の 30 秒上限より短くし、
    # 生成が長引いても API Gateway でぶら下がって 504 になる前に切って 500 を返す。
    _TIMEOUT = 25.0
    _TIMEOUT_TOOLS = 40.0  # Function Calling 用 (Lambda 60s timeout の余裕)

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LlmResponse:
        """Gemini の generateContent を Function Calling 対応で呼び出す。

        messages は共通中間形式（role / content / tool_call_id / tool_calls / tool_name）。
        本メソッド内で Gemini 固有形式（contents[].parts[]）に変換する。
        """
        url = f"{self._BASE_URL}/{self._model}:generateContent?key={self._api_key}"
        contents = _to_gemini_contents(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=self._TIMEOUT_TOOLS) as client:
                resp = client.post(url, json=payload)

            if resp.status_code == 400:
                data = resp.json()
                error_msg = data.get("error", {}).get("message", "")
                if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                    raise AiApiKeyInvalidError(
                        "Gemini APIキーが無効です。設定ページで正しいAPIキーを登録してください。"
                    )
                raise RuntimeError(f"Gemini APIエラー: {error_msg}")
            if resp.status_code == 403:
                raise AiApiKeyInvalidError("Gemini APIキーが無効です。設定ページで正しいAPIキーを登録してください。")
            if resp.status_code in (429, 503):
                raise RuntimeError(f"Gemini APIが混雑しています ({resp.status_code})")
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini APIから応答がありませんでした")

            parts = candidates[0]["content"].get("parts", [])
            content_text = ""
            tool_calls: list[ToolCall] = []
            for part in parts:
                if "text" in part:
                    content_text += part["text"]
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    # Gemini は tool_call_id を返さないため自前で発行する
                    tool_calls.append(
                        ToolCall(
                            id=f"gemini_call_{uuid.uuid4().hex[:12]}",
                            name=fc.get("name", ""),
                            arguments=dict(fc.get("args") or {}),
                        )
                    )

            usage = data.get("usageMetadata", {})
            return LlmResponse(
                content=content_text,
                model=self._model,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                tool_calls=tool_calls,
            )
        except AiApiKeyInvalidError:
            raise
        except httpx.TimeoutException as e:
            raise TimeoutError("Gemini APIがタイムアウトしました（40秒）") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini APIエラー: {e.response.status_code}") from e

    def chat(self, system_prompt: str, user_prompt: str) -> GeminiResponse:
        url = f"{self._BASE_URL}/{self._model}:generateContent?key={self._api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {
                "temperature": 0.7,
                # 回答は system prompt で 3000 文字以内に指示済み。生成時間短縮のため上限を絞る
                "maxOutputTokens": 4096,
            },
        }

        last_status = 0
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self._do_request(url, payload)
            except _RetryableError as e:
                last_status = e.status_code
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Gemini %d, %ds 後にリトライ (%d/%d)",
                        last_status,
                        delay,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    time.sleep(delay)
                else:
                    if last_status == 503:
                        raise RuntimeError("Geminiが混雑しています。少し待ってから再実行してください。") from None
                    raise RuntimeError(
                        "Gemini APIのレート制限に達しました。しばらく待ってから再試行してください。"
                    ) from None

        raise RuntimeError("Gemini API呼び出しに失敗しました")  # unreachable

    def _do_request(self, url: str, payload: dict) -> GeminiResponse:  # type: ignore[type-arg]
        try:
            with httpx.Client(timeout=self._TIMEOUT) as client:
                resp = client.post(url, json=payload)

            if resp.status_code in (429, 503):
                error_detail = resp.json().get("error", {}).get("message", "")
                logger.warning("Gemini %d: %s", resp.status_code, error_detail)
                raise _RetryableError(resp.status_code)

            if resp.status_code == 400:
                data = resp.json()
                error_msg = data.get("error", {}).get("message", "")
                if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
                    raise AiApiKeyInvalidError(
                        "Gemini APIキーが無効です。設定ページで正しいAPIキーを登録してください。"
                    )
                raise RuntimeError(f"Gemini APIエラー: {error_msg}")
            if resp.status_code == 403:
                raise AiApiKeyInvalidError("Gemini APIキーが無効です。設定ページで正しいAPIキーを登録してください。")
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("Gemini APIから応答がありませんでした")

            content = candidates[0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return GeminiResponse(
                content=content,
                model=self._model,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
            )
        except (AiApiKeyInvalidError, _RetryableError):
            raise
        except httpx.TimeoutException as e:
            raise TimeoutError("AI分析がタイムアウトしました。もう一度お試しください。") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Gemini APIエラー: {e.response.status_code}") from e


class _RetryableError(Exception):
    """429/503 リトライ用の内部例外。"""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Retryable status: {status_code}")
        self.status_code = status_code


def _to_gemini_contents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """共通中間形式 → Gemini contents 形式に変換。

    Gemini の role は user / model / function の 3 種類。
    """
    result: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "user":
            result.append({"role": "user", "parts": [{"text": m.get("content", "")}]})
        elif role == "assistant":
            parts: list[dict[str, Any]] = []
            text = m.get("content") or ""
            if text:
                parts.append({"text": text})
            for tc in m.get("tool_calls") or []:
                parts.append({"functionCall": {"name": tc.name, "args": tc.arguments}})
            if parts:
                result.append({"role": "model", "parts": parts})
        elif role == "tool":
            # tool_result は Gemini では functionResponse として user 側 role に入れる
            tool_name = m.get("tool_name", "")
            content_raw = m.get("content", "")
            try:
                response_obj = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
            except json.JSONDecodeError:
                response_obj = {"result": content_raw}
            if not isinstance(response_obj, dict):
                response_obj = {"result": response_obj}
            result.append(
                {
                    "role": "user",
                    "parts": [{"functionResponse": {"name": tool_name, "response": response_obj}}],
                }
            )
    return result
