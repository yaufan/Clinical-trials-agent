"""Canned MCP target for tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .manager import McpToolError


class FakeTarget:
    def __init__(
        self, name: str, responses: dict[str, Any | Callable[[dict[str, Any]], Any]]
    ) -> None:
        self.name = name
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((tool, arguments))
        if tool not in self.responses:
            raise McpToolError(self.name, tool, "unknown tool (fake)")
        r = self.responses[tool]
        return r(arguments) if callable(r) else r

    async def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": k, "description": "fake"} for k in self.responses]
