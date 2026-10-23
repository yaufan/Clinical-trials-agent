"""Thin async repository over SQLAlchemy models."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..schemas.run import RunEvent, RunState
from .models import Project, Run, RunEventRow


class Repo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sm = sessionmaker

    # ── projects ─────────────────────────────────────────────────────────────
    async def create_project(self, name: str, input_json: dict[str, Any]) -> Project:
        async with self.sm() as s:
            p = Project(name=name, input_json=input_json)
            s.add(p)
            await s.commit()
            await s.refresh(p)
            return p

    async def list_projects(self) -> list[Project]:
        async with self.sm() as s:
            res = await s.execute(select(Project).order_by(Project.created_at.desc()))
            return list(res.scalars())

    async def get_project(self, project_id: str) -> Project | None:
        async with self.sm() as s:
            return await s.get(Project, project_id)

    async def update_project(
        self, project_id: str, *, name: str | None = None, input_json: dict[str, Any] | None = None
    ) -> Project | None:
        async with self.sm() as s:
            p = await s.get(Project, project_id)
            if p is None:
                return None
            if name is not None:
                p.name = name
            if input_json is not None:
                p.input_json = input_json
            await s.commit()
            await s.refresh(p)
            return p

    # ── runs ─────────────────────────────────────────────────────────────────
    async def create_run(self, state: RunState) -> Run:
        async with self.sm() as s:
            r = Run(
                id=state.run_id,
                project_id=state.project_id,
                stage=state.stage.value,
                state_json=state.model_dump(mode="json"),
            )
            s.add(r)
            await s.commit()
            await s.refresh(r)
            return r

    async def save_run(self, state: RunState) -> None:
        async with self.sm() as s:
            r = await s.get(Run, state.run_id)
            if r is None:
                r = Run(id=state.run_id, project_id=state.project_id)
                s.add(r)
            r.stage = state.stage.value
            r.state_json = state.model_dump(mode="json")
            await s.commit()

    async def get_run(self, run_id: str) -> RunState | None:
        async with self.sm() as s:
            r = await s.get(Run, run_id)
            return RunState.model_validate(r.state_json) if r else None

    async def list_runs(self, project_id: str) -> list[RunState]:
        async with self.sm() as s:
            res = await s.execute(
                select(Run).where(Run.project_id == project_id).order_by(Run.created_at.desc())
            )
            return [RunState.model_validate(r.state_json) for r in res.scalars()]

    # ── events ───────────────────────────────────────────────────────────────
    async def add_event(self, run_id: str, ev: RunEvent) -> None:
        async with self.sm() as s:
            s.add(
                RunEventRow(
                    run_id=run_id,
                    ts=ev.ts,
                    type=ev.type,
                    stage=ev.stage.value if ev.stage else None,
                    message=ev.message,
                    data_json=ev.data,
                )
            )
            await s.commit()

    async def list_events(self, run_id: str, limit: int = 500) -> list[RunEvent]:
        async with self.sm() as s:
            res = await s.execute(
                select(RunEventRow)
                .where(RunEventRow.run_id == run_id)
                .order_by(RunEventRow.id.asc())
                .limit(limit)
            )
            return [
                RunEvent(
                    ts=e.ts, type=e.type, stage=e.stage, message=e.message, data=e.data_json or {}
                )
                for e in res.scalars()
            ]
