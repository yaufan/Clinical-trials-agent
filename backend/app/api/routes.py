from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from ..exporters import markdown_to_docx, render_protocol_markdown
from ..schemas.protocol_input import EXAMPLE_INPUT, ProtocolInput
from ..schemas.run import EvidenceConfirmation, RunEvent, RunStage, RunState, SectionEdit
from .manager import TERMINAL, RunManager

router = APIRouter()


def _mgr(request: Request) -> RunManager:
    return request.app.state.manager


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    input: ProtocolInput


class ProjectUpdate(BaseModel):
    name: str | None = None
    input: ProtocolInput | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    created_at: Any
    updated_at: Any
    input: dict[str, Any]
    latest_run: RunState | None = None


def _project_out(p, latest: RunState | None = None) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        name=p.name,
        created_at=p.created_at,
        updated_at=p.updated_at,
        input=p.input_json,
        latest_run=latest,
    )


# ── meta ─────────────────────────────────────────────────────────────────────
@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    return {
        "status": "ok",
        "llm": _mgr(request).llm.name,
        "mcp_servers": list(_mgr(request).mcp.targets),
    }


@router.get("/meta/schema")
async def meta_schema() -> dict[str, Any]:
    return ProtocolInput.model_json_schema()


@router.get("/meta/example")
async def meta_example() -> dict[str, Any]:
    return EXAMPLE_INPUT


@router.get("/meta/config")
async def meta_config(request: Request) -> dict[str, Any]:
    s = _mgr(request).settings
    return {
        "llm_provider": s.llm_provider,
        "llm_model": s.anthropic_model if s.llm_provider == "anthropic" else s.llm_model,
        "llm_base_url": None if s.llm_provider == "anthropic" else s.llm_base_url,
        "mcp_targets": s.mcp_targets,
    }


@router.get("/meta/mcp-health")
async def meta_mcp_health(request: Request) -> dict[str, Any]:
    return await _mgr(request).mcp.health()


# ── projects ─────────────────────────────────────────────────────────────────
@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, request: Request) -> ProjectOut:
    p = await _mgr(request).repo.create_project(body.name, body.input.model_dump(mode="json"))
    return _project_out(p)


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(request: Request) -> list[ProjectOut]:
    repo = _mgr(request).repo
    out: list[ProjectOut] = []
    for p in await repo.list_projects():
        runs = await repo.list_runs(p.id)
        out.append(_project_out(p, runs[0] if runs else None))
    return out


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, request: Request) -> ProjectOut:
    repo = _mgr(request).repo
    p = await repo.get_project(project_id)
    if p is None:
        raise HTTPException(404, "project not found")
    runs = await repo.list_runs(p.id)
    return _project_out(p, runs[0] if runs else None)


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate, request: Request) -> ProjectOut:
    p = await _mgr(request).repo.update_project(
        project_id,
        name=body.name,
        input_json=body.input.model_dump(mode="json") if body.input else None,
    )
    if p is None:
        raise HTTPException(404, "project not found")
    return _project_out(p)


# ── runs ─────────────────────────────────────────────────────────────────────
@router.post("/projects/{project_id}/runs", response_model=RunState, status_code=201)
async def start_run(project_id: str, request: Request) -> RunState:
    mgr = _mgr(request)
    p = await mgr.repo.get_project(project_id)
    if p is None:
        raise HTTPException(404, "project not found")
    return await mgr.start_run(project_id, ProtocolInput.model_validate(p.input_json))


@router.get("/projects/{project_id}/runs", response_model=list[RunState])
async def list_runs(project_id: str, request: Request) -> list[RunState]:
    return await _mgr(request).repo.list_runs(project_id)


@router.get("/runs/{run_id}", response_model=RunState)
async def get_run(run_id: str, request: Request) -> RunState:
    st = await _mgr(request).repo.get_run(run_id)
    if st is None:
        raise HTTPException(404, "run not found")
    return st


@router.get("/runs/{run_id}/events/history", response_model=list[RunEvent])
async def run_events_history(run_id: str, request: Request) -> list[RunEvent]:
    return await _mgr(request).repo.list_events(run_id)


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request):
    mgr = _mgr(request)
    state = await mgr.repo.get_run(run_id)
    if state is None:
        raise HTTPException(404, "run not found")

    async def gen():
        for ev in await mgr.repo.list_events(run_id):
            yield {"event": ev.type, "data": ev.model_dump_json()}
        current = await mgr.repo.get_run(run_id)
        if current and current.stage in TERMINAL:
            yield {"event": "done", "data": json.dumps({"stage": current.stage.value})}
            return
        q = mgr.subscribe(run_id)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15.0)
                except TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                if ev is None:
                    latest = await mgr.repo.get_run(run_id)
                    yield {
                        "event": "done",
                        "data": json.dumps({"stage": latest.stage.value if latest else "unknown"}),
                    }
                    break
                yield {"event": ev.type, "data": ev.model_dump_json()}
        finally:
            mgr.unsubscribe(run_id, q)

    return EventSourceResponse(gen())


@router.post("/runs/{run_id}/confirm-evidence", response_model=RunState)
async def confirm_evidence(run_id: str, body: EvidenceConfirmation, request: Request) -> RunState:
    mgr = _mgr(request)
    state = await mgr.repo.get_run(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    project = await mgr.repo.get_project(state.project_id)
    try:
        return await mgr.confirm_evidence(
            run_id, ProtocolInput.model_validate(project.input_json), body
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.put("/runs/{run_id}/sections/{key}", response_model=RunState)
async def edit_section(run_id: str, key: str, body: SectionEdit, request: Request) -> RunState:
    try:
        return await _mgr(request).edit_section(run_id, key, body)
    except KeyError as exc:
        raise HTTPException(404, "run not found") from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/runs/{run_id}/cancel", response_model=RunState)
async def cancel_run(run_id: str, request: Request) -> RunState:
    st = await _mgr(request).cancel(run_id)
    if st is None:
        raise HTTPException(404, "run not found")
    return st


async def _render(run_id: str, request: Request) -> tuple[str, RunState]:
    mgr = _mgr(request)
    state = await mgr.repo.get_run(run_id)
    if state is None:
        raise HTTPException(404, "run not found")
    project = await mgr.repo.get_project(state.project_id)
    inp = ProtocolInput.model_validate(project.input_json)
    return render_protocol_markdown(inp, state), state


@router.get("/runs/{run_id}/export.md")
async def export_md(run_id: str, request: Request) -> PlainTextResponse:
    md, state = await _render(run_id, request)
    return PlainTextResponse(
        md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="protocol-{state.run_id[:8]}.md"'},
    )


@router.get("/runs/{run_id}/export.docx")
async def export_docx(run_id: str, request: Request) -> Response:
    md, state = await _render(run_id, request)
    data = markdown_to_docx(md)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="protocol-{state.run_id[:8]}.docx"'},
    )


_ = RunStage  # keep import for type re-export
