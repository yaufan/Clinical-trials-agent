"""Orchestrates the five agents with persistence, events and the human-in-the-loop gate."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from ..config import Settings
from ..llm.base import LLMClient
from ..mcp_client.manager import McpManager
from ..schemas.protocol_input import ProtocolInput
from ..schemas.run import EvidenceConfirmation, RunEvent, RunStage, RunState, utcnow
from .auditor import run_audit
from .base import AgentContext, EmitFn
from .biostat import run_biostat
from .harvester import run_harvest
from .triage import run_triage
from .writer import revise_section, run_writer

log = logging.getLogger(__name__)

SaveFn = Callable[[RunState], Awaitable[None]]


class Pipeline:
    def __init__(
        self, *, llm: LLMClient, mcp: McpManager, settings: Settings, save: SaveFn, emit: EmitFn
    ) -> None:
        self.llm, self.mcp, self.settings, self.save, self.emit = llm, mcp, settings, save, emit

    def _ctx(self, state: RunState, inp: ProtocolInput) -> AgentContext:
        return AgentContext(
            llm=self.llm,
            mcp=self.mcp,
            settings=self.settings,
            state=state,
            input=inp,
            emit=self.emit,
        )

    async def _enter(self, state: RunState, stage: RunStage) -> None:
        state.stage = stage
        state.updated_at = utcnow()
        await self.save(state)
        await self.emit(
            RunEvent(type="stage_started", stage=stage, message=f"{stage.value} started")
        )

    async def _done(self, state: RunState, stage: RunStage) -> None:
        state.updated_at = utcnow()
        state.tool_calls = self.mcp.calls
        await self.save(state)
        await self.emit(
            RunEvent(type="stage_completed", stage=stage, message=f"{stage.value} completed")
        )

    # ── public entry points ──────────────────────────────────────────────────
    async def run_until_gate(self, state: RunState, inp: ProtocolInput) -> RunState:
        """Stages 1–2, then park at the evidence-confirmation gate."""
        ctx = self._ctx(state, inp)
        try:
            await self._enter(state, RunStage.triage)
            state.triage = await run_triage(ctx)
            await self._done(state, RunStage.triage)

            await self._enter(state, RunStage.harvest)
            state.evidence = await run_harvest(ctx)
            await self._done(state, RunStage.harvest)

            state.stage = RunStage.awaiting_evidence_confirmation
            state.updated_at = utcnow()
            await self.save(state)
            await self.emit(
                RunEvent(
                    type="hitl_required",
                    stage=state.stage,
                    message="Please review the evidence matrix and confirm to continue",
                    data={"n_items": len(state.evidence.items)},
                )
            )
        except asyncio.CancelledError:
            await self._cancel(state)
            raise
        except Exception as exc:
            await self._fail(state, exc)
        return state

    async def apply_confirmation(
        self, state: RunState, confirmation: EvidenceConfirmation
    ) -> RunState:
        if state.evidence is None:
            raise ValueError("run has no evidence matrix to confirm")
        ev = state.evidence
        if confirmation.accepted_ref_ids is not None:
            keep = set(confirmation.accepted_ref_ids)
            for it in ev.items:
                it.accepted = it.ref_id in keep
        for ref, note in confirmation.item_notes.items():
            for it in ev.items:
                if it.ref_id == ref:
                    it.user_note = note
        ev.baseline_performance.update(confirmation.baseline_overrides)
        ev.reviewer_notes = confirmation.reviewer_notes
        ev.confirmed = True
        ev.confirmed_at = utcnow()
        state.updated_at = utcnow()
        await self.save(state)
        await self.emit(
            RunEvent(
                type="log",
                stage=state.stage,
                message="Evidence confirmed by reviewer",
                data={"accepted": sum(i.accepted for i in ev.items)},
            )
        )
        return state

    async def run_after_gate(self, state: RunState, inp: ProtocolInput) -> RunState:
        """Stages 3–5 (requires a confirmed evidence matrix)."""
        ctx = self._ctx(state, inp)
        try:
            await self._enter(state, RunStage.biostat)
            state.sap = await run_biostat(ctx, state.evidence)
            await self._done(state, RunStage.biostat)

            await self._enter(state, RunStage.write)
            state.sections = await run_writer(
                ctx, triage=state.triage, evidence=state.evidence, sap=state.sap
            )
            await self._done(state, RunStage.write)

            await self._enter(state, RunStage.audit)
            for iteration in range(1, self.settings.max_audit_iterations + 1):
                report = await run_audit(
                    ctx, state.sections, triage=state.triage, iteration=iteration
                )
                state.audits.append(report)
                await self.save(state)
                if not report.revision_requests or iteration == self.settings.max_audit_iterations:
                    break
                await ctx.progress(
                    "Audit: revising sections", sections=list(report.revision_requests)
                )
                for key, fixes in report.revision_requests.items():
                    sec = state.section(key)
                    if sec is None:
                        continue
                    revised = await revise_section(ctx, sec, fixes, sap=state.sap)
                    state.sections = [revised if s.key == key else s for s in state.sections]
                await self.save(state)
            await self._done(state, RunStage.audit)

            state.stage = RunStage.completed
            state.updated_at = utcnow()
            await self.save(state)
            await self.emit(
                RunEvent(
                    type="stage_completed",
                    stage=RunStage.completed,
                    message="Protocol draft completed",
                )
            )
        except asyncio.CancelledError:
            await self._cancel(state)
            raise
        except Exception as exc:
            await self._fail(state, exc)
        return state

    async def _fail(self, state: RunState, exc: Exception) -> None:
        log.exception("run %s failed in stage %s", state.run_id, state.stage)
        state.error = f"{type(exc).__name__}: {exc}"
        state.stage = RunStage.failed
        state.updated_at = utcnow()
        await self.save(state)
        await self.emit(RunEvent(type="error", stage=RunStage.failed, message=state.error))

    async def _cancel(self, state: RunState) -> None:
        state.stage = RunStage.cancelled
        state.updated_at = utcnow()
        await self.save(state)
        await self.emit(RunEvent(type="log", stage=RunStage.cancelled, message="Run cancelled"))
