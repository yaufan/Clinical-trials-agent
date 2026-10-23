"""Provider-agnostic LLM interface used by every agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


class LLMError(RuntimeError):
    pass


class LLMRefusal(LLMError):
    """The model (or a safety layer) declined to answer."""


@dataclass
class LLMMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class LLMResponse:
    text: str
    parsed: Any | None = None
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None
    raw: Any = field(default=None, repr=False)


class LLMClient(Protocol):
    name: str

    async def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        json_schema: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse: ...


_THINK_RE = re.compile(r"<think>.*?</think>", re.S)
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)


def strip_reasoning(text: str) -> str:
    """Remove <think>…</think> blocks emitted by reasoning models (Qwen3, DeepSeek-R1 …)."""
    return _THINK_RE.sub("", text).strip()


def extract_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM reply (code fences, leading prose, trailing text)."""
    text = strip_reasoning(text)
    candidates: list[str] = []
    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1))
    candidates.append(text)
    for cand in candidates:
        cand = cand.strip()
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
        # locate first balanced {...} or [...]
        for opener, closer in (("{", "}"), ("[", "]")):
            start = cand.find(opener)
            if start == -1:
                continue
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(cand)):
                ch = cand[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(cand[start : i + 1])
                        except json.JSONDecodeError:
                            break
    raise LLMError("no JSON object found in model output")
