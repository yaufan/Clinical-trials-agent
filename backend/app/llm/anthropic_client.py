"""Claude via the official Anthropic SDK (optional cloud provider).

Defaults follow current API conventions: `claude-opus-5-5`, adaptive thinking (the default on
this model — no `thinking` parameter is sent), explicit `output_config.effort`, streaming with
`get_final_message()` so long protocol sections never hit HTTP timeouts, and structured
outputs through `output_config.format` (JSON Schema). A `stop_reason == "refusal"` is surfaced
as :class:`LLMRefusal`.
"""

from __future__ import annotations

from typing import Any

from .base import LLMError, LLMMessage, LLMRefusal, LLMResponse, extract_json


class AnthropicLLM:
    def __init__(
        self,
        *,
        model: str = "claude-opus-5-5",
        api_key: str | None = None,
        max_tokens: int = 16000,
        effort: str = "high",
        client: Any | None = None,
    ) -> None:
        if client is None:
            import anthropic

            client = (
                anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
            )
        self._client = client
        self.model = model
        self.name = f"anthropic:{model}"
        self.max_tokens = max_tokens
        self.effort = effort

    async def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,  # not supported on current models; ignored
    ) -> LLMResponse:
        output_config: dict[str, Any] = {"effort": self.effort}
        if json_schema:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=system,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            output_config=output_config,
        )
        try:
            async with self._client.messages.stream(**kwargs) as stream:
                message = await stream.get_final_message()
        except Exception as exc:  # anthropic.APIError family
            raise LLMError(f"Anthropic API error: {exc}") from exc

        if getattr(message, "stop_reason", None) == "refusal":
            details = getattr(message, "stop_details", None)
            raise LLMRefusal(f"model refused: {getattr(details, 'category', None)}")
        text = "".join(
            getattr(b, "text", "") for b in message.content if getattr(b, "type", "") == "text"
        )
        usage = getattr(message, "usage", None)
        return LLMResponse(
            text=text,
            parsed=extract_json(text) if json_schema else None,
            model=getattr(message, "model", self.model),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            stop_reason=getattr(message, "stop_reason", None),
            raw=message,
        )
