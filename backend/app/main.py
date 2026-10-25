"""FastAPI application factory."""

from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    if settings.api_key:
        exempt = {f"{settings.api_prefix}/health"}

        @app.middleware("http")
        async def require_api_key(request: Request, call_next):
            path = request.url.path
            if (
                request.method == "OPTIONS"
                or not path.startswith(settings.api_prefix)
                or path in exempt
            ):
                return await call_next(request)
            presented = request.headers.get("x-api-key") or ""
            auth = request.headers.get("authorization") or ""
            if auth.lower().startswith("bearer "):
                presented = presented or auth[7:].strip()
            if not presented or not hmac.compare_digest(presented, settings.api_key):
                return JSONResponse(
                    {"detail": "missing or invalid API key"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)

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
