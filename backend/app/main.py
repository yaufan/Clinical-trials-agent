"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.manager import RunManager
from .api.routes import router
from .config import Settings, get_settings
from .db import Database, Repo
from .llm import build_llm
from .llm.base import LLMClient
from .mcp_client.manager import McpManager, manager_from_urls

log = logging.getLogger("app")


def create_app(
    settings: Settings | None = None,
    *,
    llm: LLMClient | None = None,
    mcp: McpManager | None = None,
    database: Database | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    db = database or Database(settings.database_url)
    llm = llm or build_llm(settings)
    mcp = mcp or manager_from_urls(
        settings.mcp_targets, read_timeout_seconds=settings.mcp_call_timeout_seconds
    )
    manager = RunManager(repo=Repo(db.sessionmaker), llm=llm, mcp=mcp, settings=settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db.init()
        log.info("LLM provider: %s · MCP servers: %s", llm.name, list(mcp.targets))
        yield
        await manager.shutdown()
        await db.close()

    app = FastAPI(title="AI-SaMD Clinical Protocol Copilot API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.api_prefix)
    app.state.manager = manager
    app.state.db = db
    app.state.settings = settings
    return app


def build() -> FastAPI:
    """uvicorn factory: `uvicorn app.main:build --factory`."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    return create_app()
