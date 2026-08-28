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

# 個別株 AI 分析の出力設定。
# gemini-2.5-flash は thinkingBudget 未指定だと dynamic thinking (-1) で動き、
# 思考トークンが出力枠を圧迫して本文が途中で切れる事象があったため、予算を明示的に固定する。
# 有効範囲は 0〜24576。0 で thinking 無効。
_THINKING_BUDGET = 1024
_MAX_OUTPUT_TOKENS = 8192


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
                # 回答は system prompt で 3000 文字以内に指示済み。
                # thinking の消費分を見込んで本文が切れないよう枠を確保する。
                "maxOutputTokens": _MAX_OUTPUT_TOKENS,
                "thinkingConfig": {"thinkingBudget": _THINKING_BUDGET},
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
        started = time.monotonic()
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

            # thinking 有効時は parts が複数に分かれることがあるため全 text を連結する
            # (parts[0] 決め打ちだと本文の先頭断片しか取れない)
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p["text"] for p in parts if "text" in p)

            usage = data.get("usageMetadata", {})
            thoughts_tokens = usage.get("thoughtsTokenCount", 0)
            elapsed = time.monotonic() - started

            finish_reason = candidates[0].get("finishReason")
            if finish_reason == "MAX_TOKENS":
                logger.warning(
                    "Gemini 応答が maxOutputTokens(%d) で打ち切られました (thinking=%d, completion=%d, %.1fs)",
                    _MAX_OUTPUT_TOKENS,
                    thoughts_tokens,
                    usage.get("candidatesTokenCount", 0),
                    elapsed,
                )
            if not content:
                raise RuntimeError("Gemini APIから本文が返りませんでした")

            logger.info(
                "Gemini 応答: %.1fs prompt=%d thinking=%d completion=%d chars=%d finish=%s",
                elapsed,
                usage.get("promptTokenCount", 0),
                thoughts_tokens,
                usage.get("candidatesTokenCount", 0),
                len(content),
                finish_reason,
            )

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
