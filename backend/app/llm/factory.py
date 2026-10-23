from __future__ import annotations

from ..config import Settings
from .anthropic_client import AnthropicLLM
from .base import LLMClient
from .fake import FakeLLM
from .openai_compat import OpenAICompatibleLLM


def build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "fake":
        return FakeLLM()
    if settings.llm_provider == "anthropic":
        return AnthropicLLM(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            max_tokens=max(settings.llm_max_tokens, 16000),
        )
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout_seconds,
    )
