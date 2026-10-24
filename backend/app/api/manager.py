"""RunManager: background execution, event fan-out (SSE) and the human-in-the-loop gate."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict

from ..agents.pipeline import Pipeline
from ..config import Settings
from ..db.repo import Repo
from ..llm.base import LLMClient
from ..mcp_client.manager import McpManager
from ..schemas.protocol_input import ProtocolInput
from ..schemas.run import EvidenceConfirmation, RunEvent, RunStage, RunState, SectionEdit, utcnow

log = logging.getLogger(__name__)

TERMINAL = {RunStage.completed, RunStage.failed, RunStage.cancelled}


class RunManager:
    def __init__(self, *, repo: Repo, llm: LLMClient, mcp: McpManager, settings: Settings) -> None:
        self.repo, self.llm, self.mcp, self.settings = repo, llm, mcp, settings
        self.tasks: dict[str, asyncio.Task[RunState]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[RunEvent | None]]] = defaultdict(set)

    # ── events ───────────────────────────────────────────────────────────────
    def _emitter(self, run_id: str):
        async def emit(ev: RunEvent) -> None:
            try:
                await self.repo.add_event(run_id, ev)
            except Exception:  # pragma: no cover
                log.exception("failed to persist event")
            for q in list(self._subscribers.get(run_id, ())):
                q.put_nowait(ev)
            if (
                ev.type in ("stage_completed", "error")
                and ev.stage in TERMINAL
                or ev.type == "log"
                and ev.stage == RunStage.cancelled
            ):
                for q in list(self._subscribers.get(run_id, ())):
                    q.put_nowait(None)

        return emit

    def subscribe(self, run_id: str) -> asyncio.Queue[RunEvent | None]:
        q: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        self._subscribers[run_id].add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue[RunEvent | None]) -> None:
        self._subscribers[run_id].discard(q)

    def _pipeline(self, run_id: str) -> Pipeline:
        emit = self._emitter(run_id)

        async def on_tool_call(
            server: str, tool: str, arguments: dict, seconds: float, ok: bool
        ) -> None:
            await emit(
                RunEvent(
                    type="tool_call",
                    message=f"{server}.{tool} ({seconds:.1f}s){'' if ok else ' FAILED'}",
                    data={"server": server, "tool": tool, "ok": ok, "seconds": round(seconds, 2)},
                )
            )

        # one manager per run so tool-call counts are per run, not per process
        run_mcp = McpManager(self.mcp.targets, hook=on_tool_call)
        return Pipeline(
            llm=self.llm, mcp=run_mcp, settings=self.settings, save=self.repo.save_run, emit=emit
        )

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start_run(self, project_id: str, inp: ProtocolInput) -> RunState:
        state = RunState(run_id=str(uuid.uuid4()), project_id=project_id)
        await self.repo.create_run(state)
        pipeline = self._pipeline(state.run_id)
        self.tasks[state.run_id] = asyncio.create_task(
            pipeline.run_until_gate(state, inp), name=f"run:{state.run_id}:gate"
        )
        return state

    async def confirm_evidence(
        self, run_id: str, inp: ProtocolInput, confirmation: EvidenceConfirmation
    ) -> RunState:
        state = await self.repo.get_run(run_id)
        if state is None:
            raise KeyError(run_id)
        if state.stage != RunStage.awaiting_evidence_confirmation:
            raise ValueError(f"run is in stage {state.stage.value}, not awaiting confirmation")
        pipeline = self._pipeline(run_id)
        state = await pipeline.apply_confirmation(state, confirmation)
        self.tasks[run_id] = asyncio.create_task(
            pipeline.run_after_gate(state, inp), name=f"run:{run_id}:after"
        )
        return state

    async def cancel(self, run_id: str) -> RunState | None:
        task = self.tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        state = await self.repo.get_run(run_id)
        if state and state.stage not in TERMINAL:
            state.stage = RunStage.cancelled
            state.updated_at = utcnow()
            await self.repo.save_run(state)
        return state

    async def edit_section(self, run_id: str, key: str, edit: SectionEdit) -> RunState:
        state = await self.repo.get_run(run_id)
        if state is None:
            raise KeyError(run_id)
        sec = state.section(key)
        if sec is None:
            raise ValueError(f"unknown section {key}")
        sec.markdown = edit.markdown
        sec.revision += 1
        sec.last_edited_by = edit.editor
        state.updated_at = utcnow()
        await self.repo.save_run(state)
        return state

    async def wait(self, run_id: str, max_seconds: float | None = None) -> RunState | None:
        task = self.tasks.get(run_id)
        if task:
            await asyncio.wait_for(asyncio.shield(task), max_seconds)
        return await self.repo.get_run(run_id)

    async def shutdown(self) -> None:
        for t in self.tasks.values():
            if not t.done():
                t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
