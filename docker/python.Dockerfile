# Shared image for the FastAPI backend and all five MCP servers.
# Multi-arch (linux/amd64 + linux/arm64) — builds natively on the DGX Spark (GB10, aarch64).
#
#   docker build -f docker/python.Dockerfile -t aisamd-python .
#   docker run --rm aisamd-python python -m mcp_biostat_calc --transport streamable-http --port 8101
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# uv (static binary, multi-arch image)
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /app

# 1) dependency layer — only manifests, so code edits don't bust the cache
COPY pyproject.toml uv.lock README.md ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY mcp-servers/mcp-biostat-calc/pyproject.toml      mcp-servers/mcp-biostat-calc/pyproject.toml
COPY mcp-servers/mcp-clinicaltrials/pyproject.toml    mcp-servers/mcp-clinicaltrials/pyproject.toml
COPY mcp-servers/mcp-openfda-predicate/pyproject.toml mcp-servers/mcp-openfda-predicate/pyproject.toml
COPY mcp-servers/mcp-pubmed-evidence/pyproject.toml   mcp-servers/mcp-pubmed-evidence/pyproject.toml
COPY mcp-servers/mcp-regulatory-rag/pyproject.toml    mcp-servers/mcp-regulatory-rag/pyproject.toml
RUN uv sync --frozen --no-dev --all-packages --no-install-workspace

# 2) source layer
COPY backend backend
COPY mcp-servers mcp-servers
RUN uv sync --frozen --no-dev --all-packages

# non-root runtime user; /data holds sqlite/corpus caches when not using Postgres/Qdrant
RUN useradd -r -u 10001 -m copilot && mkdir -p /data && chown -R copilot:copilot /data /app
USER copilot
ENV PYTHONPATH=/app/backend
EXPOSE 8000 8101 8102 8103 8104 8105
CMD ["uvicorn", "app.main:build", "--factory", "--host", "0.0.0.0", "--port", "8000"]
