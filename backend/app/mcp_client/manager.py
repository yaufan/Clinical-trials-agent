"""Connects the agents to MCP servers (streamable HTTP in production, in-process in tests)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from mcp.client.client import Client

log = logging.getLogger(__name__)

ToolCallHook = Callable[[str, str, dict[str, Any], float, bool], Awaitable[None]]


class McpToolError(RuntimeError):
    def __init__(self, server: str, tool: str, message: str) -> None:
        super().__init__(f"{server}.{tool}: {message}")
        self.server, self.tool, self.detail = server, tool, message


class McpTarget(Protocol):
    async def call(self, tool: str, arguments: dict[str, Any]) -> Any: ...
    async def list_tools(self) -> list[dict[str, Any]]: ...


def unwrap_result(result: Any, *, server: str, tool: str) -> Any:
    """Normalise a CallToolResult → python object (dict / list / scalar)."""
    if getattr(result, "is_error", False):
        text = " ".join(getattr(c, "text", "") for c in (result.content or []))
        raise McpToolError(server, tool, text or "tool error")
    sc = getattr(result, "structured_content", None)
    if sc is not None:
        if isinstance(sc, dict) and set(sc) == {"result"}:
            return sc["result"]
        return sc
    texts = [
        getattr(c, "text", "") for c in (result.content or []) if getattr(c, "type", "") == "text"
    ]
    joined = "\n".join(texts)
    try:
        return json.loads(joined)
    except json.JSONDecodeError:
        return joined


class ClientTarget:
    """Any target the official `mcp.client.client.Client` accepts: a URL string or an in-process MCPServer."""

    def __init__(self, target: Any, *, name: str, read_timeout_seconds: float = 180.0) -> None:
        self._target = target
        self.name = name
        self._timeout = read_timeout_seconds

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        async with Client(self._target, read_timeout_seconds=self._timeout) as client:
            result = await client.call_tool(tool, arguments)
        return unwrap_result(result, server=self.name, tool=tool)

    async def list_tools(self) -> list[dict[str, Any]]:
        async with Client(self._target, read_timeout_seconds=self._timeout) as client:
            res = await client.list_tools()
        return [{"name": t.name, "description": t.description or ""} for t in res.tools]


class McpManager:
    def __init__(self, targets: dict[str, McpTarget], *, hook: ToolCallHook | None = None) -> None:
        self.targets = targets
        self.hook = hook
        self.calls = 0

    def has(self, server: str) -> bool:
        return server in self.targets

    async def call(self, server: str, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        if server not in self.targets:
            raise McpToolError(server, tool, "server not configured")
        arguments = arguments or {}
        t0 = time.perf_counter()
        ok = True
        try:
            result = await self.targets[server].call(tool, arguments)
            self.calls += 1
            return result
        except Exception:
            ok = False
            raise
        finally:
            if self.hook:
                try:
                    await self.hook(server, tool, arguments, time.perf_counter() - t0, ok)
                except Exception:  # pragma: no cover - hooks must never break a call
                    log.exception("tool hook failed")

    async def try_call(
        self,
        server: str,
        tool: str,
        arguments: dict[str, Any] | None = None,
        *,
        default: Any = None,
        warnings: list[str] | None = None,
    ) -> Any:
        """Call and swallow failures (evidence sources are best-effort)."""
        try:
            return await self.call(server, tool, arguments)
        except Exception as exc:
            msg = f"{server}.{tool} failed: {exc}"
            log.warning(msg)
            if warnings is not None:
                warnings.append(msg)
            return default

    async def health(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, target in self.targets.items():
            try:
                tools = await target.list_tools()
                out[name] = {"ok": True, "tools": [t["name"] for t in tools]}
            except Exception as exc:
                out[name] = {"ok": False, "error": str(exc)[:200]}
        return out


def manager_from_urls(
    urls: dict[str, str], *, read_timeout_seconds: float = 180.0, hook: ToolCallHook | None = None
) -> McpManager:
    return McpManager(
        {
            name: ClientTarget(url, name=name, read_timeout_seconds=read_timeout_seconds)
            for name, url in urls.items()
        },
        hook=hook,
    )
