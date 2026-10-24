"""OpenAI-compatible chat-completions client (vLLM / Ollama / NVIDIA NIM / llama.cpp on the GB10).

Structured output: first tries `response_format={"type":"json_schema",…}` (vLLM guided decoding,
Ollama ≥ 0.5 structured outputs); on a 400 it falls back to `json_object`, then to free text +
robust JSON extraction, so any OpenAI-compatible server works.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .base import LLMError, LLMMessage, LLMResponse, LLMTruncated, extract_json, strip_reasoning

log = logging.getLogger(__name__)


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.2,
        timeout: float = 600.0,
        client: httpx.AsyncClient | None = None,
        extra_body: dict[str, Any] | None = None,
        max_tokens_cap: int = 24000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.name = f"openai-compatible:{model}"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.extra_body = extra_body or {}
        self.max_tokens_cap = max(max_tokens, max_tokens_cap)
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=30.0), headers=headers
        )
        self._structured_mode: str | None = (
            None  # learned capability: json_schema | json_object | none
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Chat completion with automatic recovery from truncated / reasoning-only replies.

        Reasoning models (Qwen3, DeepSeek-R1 …) spend output tokens on thinking first; if the
        budget runs out the visible answer is empty or cut off. We retry with a doubled budget
        up to ``max_tokens_cap`` before giving up.
        """
        budget = max_tokens or self.max_tokens
        attempt = 0
        while True:
            try:
                return await self._complete_once(system, messages, json_schema, budget, temperature)
            except LLMTruncated as exc:
                attempt += 1
                if attempt >= 3 or budget >= self.max_tokens_cap:
                    raise
                new_budget = min(budget * 2, self.max_tokens_cap)
                log.warning(
                    "LLM reply truncated (%s); retrying with max_tokens=%d", exc, new_budget
                )
                budget = new_budget

    async def _complete_once(
        self,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float | None,
    ) -> LLMResponse:
        modes = ["json_schema", "json_object", "none"] if json_schema else ["none"]
        if self._structured_mode and json_schema:
            modes = modes[modes.index(self._structured_mode) :]
        last_exc: Exception | None = None
        for mode in modes:
            body = self._body(system, messages, json_schema, mode, max_tokens, temperature)
            try:
                data = await self._post_with_retry(body)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 400 and mode != "none":
                    log.info(
                        "server rejected response_format mode=%s; falling back (%s)",
                        mode,
                        exc.response.text[:200],
                    )
                    last_exc = exc
                    continue
                raise LLMError(
                    f"LLM HTTP {exc.response.status_code}: {exc.response.text[:500]}"
                ) from exc
            if json_schema:
                self._structured_mode = mode
            return self._parse(data, json_schema is not None)
        raise LLMError(f"LLM request failed: {last_exc}")

    def _body(
        self,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None,
        mode: str,
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        msgs: list[dict[str, str]] = []
        sys_text = system
        if json_schema and mode != "json_schema":
            sys_text += (
                "\n\nRespond ONLY with a single JSON object that conforms to this JSON Schema (no prose, no code fences):\n"
                + _compact(json_schema)
            )
        msgs.append({"role": "system", "content": sys_text})
        msgs.extend({"role": m.role, "content": m.content} for m in messages)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
            "stream": False,
        }
        if json_schema and mode == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema.get("title", "response"),
                    "schema": json_schema,
                    "strict": False,
                },
            }
        elif json_schema and mode == "json_object":
            body["response_format"] = {"type": "json_object"}
        body.update(self.extra_body)
        return body

    async def _post_with_retry(self, body: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        delay = 2.0
        for attempt in range(1, attempts + 1):
            try:
                resp = await self._client.post(f"{self.base_url}/chat/completions", json=body)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < attempts:
                    raise httpx.TransportError(f"retryable status {resp.status_code}")
                resp.raise_for_status()
                return resp.json()
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                if attempt == attempts:
                    raise LLMError(f"LLM unreachable after {attempts} attempts: {exc}") from exc
                await asyncio.sleep(delay)
                delay *= 2
        raise LLMError("unreachable")  # pragma: no cover

    def _parse(self, data: dict[str, Any], want_json: bool) -> LLMResponse:
        try:
            choice = data["choices"][0]
            msg = choice["message"]
            text = msg.get("content") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"malformed completion payload: {str(data)[:300]}") from exc
        reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
        text = strip_reasoning(text)
        finish = choice.get("finish_reason")
        if finish == "length":
            raise LLMTruncated(
                f"finish_reason=length (content {len(text)} chars, reasoning {len(reasoning)} chars)"
            )
        if not text.strip() and reasoning:
            raise LLMTruncated("model returned reasoning but no answer")
        usage = data.get("usage") or {}
        try:
            parsed = extract_json(text) if want_json else None
        except LLMError as exc:
            if want_json and len(text) > 0.8 * max(1, 4 * (usage.get("completion_tokens") or 0)):
                raise LLMTruncated(f"unparseable JSON, likely cut off: {exc}") from exc
            raise
        return LLMResponse(
            text=text,
            parsed=parsed,
            model=data.get("model", self.model),
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            stop_reason=choice.get("finish_reason"),
            raw=data,
        )


def _compact(schema: dict[str, Any]) -> str:
    import json

    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
