.PHONY: sync test lint fmt build-frontend compose-up compose-down ingest smoke

sync:            ## Install every Python workspace member into .venv
	uv sync --all-packages --group dev

test:            ## Run all Python tests
	uv run pytest -q

lint:            ## Ruff lint + format check
	uv run ruff check . && uv run ruff format --check .

fmt:             ## Auto-format
	uv run ruff format . && uv run ruff check --fix .

build-frontend:  ## Type-check and build the Next.js app
	cd frontend && npm ci && npm run build

compose-up:      ## Start the full stack on the GB10 (Ollama profile)
	docker compose --profile ollama up -d --build

compose-down:
	docker compose --profile ollama --profile vllm down

ingest:          ## Download guidance PDFs and index them into Qdrant
	uv run python -m mcp_regulatory_rag.ingest --sources mcp-servers/mcp-regulatory-rag/sources.yaml

smoke:           ## End-to-end smoke test against a running stack
	uv run python scripts/smoke_test.py
