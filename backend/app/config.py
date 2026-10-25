"""Runtime configuration (12-factor; see .env.example at the repository root)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: Literal["local", "anthropic", "fake"] = "local"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen3:32b"
    llm_api_key: str = "not-needed"
    llm_max_tokens: int = 8192
    llm_section_max_tokens: int = 12000  # writer / revise / SAP / audit calls (long outputs)
    llm_max_tokens_cap: int = 24000  # upper bound when retrying after truncation
    llm_extra_body: str = (
        ""  # JSON merged into every chat request, e.g. {"reasoning_effort":"none"}
    )
    llm_timeout_seconds: float = 3600.0
    llm_temperature: float = 0.2
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"

    # Storage
    database_url: str = "sqlite+aiosqlite:///data/copilot.db"

    # MCP endpoints (streamable HTTP). Leave empty to disable a source.
    mcp_biostat_url: str = "http://localhost:8101/mcp"
    mcp_clinicaltrials_url: str = "http://localhost:8102/mcp"
    mcp_openfda_url: str = "http://localhost:8103/mcp"
    mcp_pubmed_url: str = "http://localhost:8104/mcp"
    mcp_regulatory_rag_url: str = "http://localhost:8105/mcp"
    mcp_call_timeout_seconds: float = 180.0

    # Pipeline
    max_audit_iterations: int = 2
    writer_concurrency: int = 3
    harvest_max_trials: int = 15
    harvest_max_predicates: int = 8
    harvest_max_articles: int = 12

    # API
    cors_origins: str = "http://localhost:3000"
    api_prefix: str = "/api"
    api_key: str = (
        ""  # when set, every /api/* request (except /api/health) must send X-API-Key or Bearer
    )

    @property
    def llm_extra_body_dict(self) -> dict:
        import json

        if not self.llm_extra_body.strip():
            return {}
        try:
            parsed = json.loads(self.llm_extra_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM_EXTRA_BODY is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM_EXTRA_BODY must be a JSON object")
        return parsed

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def mcp_targets(self) -> dict[str, str]:
        pairs = {
            "biostat": self.mcp_biostat_url,
            "clinicaltrials": self.mcp_clinicaltrials_url,
            "openfda": self.mcp_openfda_url,
            "pubmed": self.mcp_pubmed_url,
            "regulatory_rag": self.mcp_regulatory_rag_url,
        }
        return {k: v for k, v in pairs.items() if v}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


_ = Field  # re-exported for type checkers
