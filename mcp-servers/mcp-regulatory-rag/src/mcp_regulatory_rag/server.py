"""MCP tool surface for mcp-regulatory-rag."""

from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from . import checklists as ck
from .ingest import make_store
from .store import GuidanceStore, RetrievedClause

INSTRUCTIONS = """Regulatory guidance retrieval and reporting-checklist tools for AI-SaMD protocols.
- retrieve_guideline_clauses: hybrid (dense + BM25) search over indexed TFDA / FDA / IMDRF guidance;
  always cite the returned `citation` strings in the protocol.
- select_checklists: decides which checklists apply to a study design (SPIRIT-AI only for
  interventional trials; STARD-AI for standalone/MRMC diagnostic accuracy; TRIPOD+AI for prediction models).
- prescreen_checklist_coverage: deterministic keyword pre-screen of draft sections; it does NOT
  replace an item-by-item audit."""

server = MCPServer(
    name="mcp-regulatory-rag",
    title="Regulatory Guidance RAG & Checklists (AI-SaMD)",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)

_store: GuidanceStore | None = None


def get_store() -> GuidanceStore:
    global _store
    if _store is None:
        _store = make_store(
            os.environ.get("QDRANT_URL"), os.environ.get("QDRANT_COLLECTION", "regulatory_guidance")
        )
        _store.ensure_collection()
    return _store


def set_store(store: GuidanceStore | None) -> None:
    """Dependency injection hook for tests / embedding."""
    global _store
    _store = store


class RetrievalResult(BaseModel):
    query: str
    filters: dict[str, str | None]
    results: list[RetrievedClause]
    embedder: str
    note: str | None = None


@server.tool(
    description=(
        "Hybrid semantic + keyword search over indexed regulatory guidance (TFDA AI/ML SaMD guidance, "
        "FDA CADe / PCCP / AI lifecycle guidances, IMDRF N41, indexed checklists). Filter by jurisdiction "
        "(TW|US|EU|INTL), document_id or doc_type. Returns clause excerpts with citations."
    )
)
def retrieve_guideline_clauses(
    query: str,
    jurisdiction: str | None = None,
    document_id: str | None = None,
    doc_type: str | None = None,
    top_k: int = 8,
) -> RetrievalResult:
    store = get_store()
    note = None
    if store.count() == 0:
        note = "Index is empty — run `python -m mcp_regulatory_rag.ingest --sources sources.yaml --include-checklists`."
    results = store.search(
        query,
        top_k=max(1, min(top_k, 30)),
        jurisdiction=jurisdiction,
        document_id=document_id,
        doc_type=doc_type,
    )
    if store.embedder.name == "hashing-fallback" and note is None:
        note = "Dense embeddings use the offline hashing fallback (set EMBEDDINGS_BASE_URL for bge-m3); ranking relies mainly on BM25."
    return RetrievalResult(
        query=query,
        filters={"jurisdiction": jurisdiction, "document_id": document_id, "doc_type": doc_type},
        results=results,
        embedder=store.embedder.name,
        note=note,
    )


@server.tool(description="List the documents currently in the guidance index with chunk counts.")
def list_indexed_documents() -> dict[str, Any]:
    store = get_store()
    return {
        "collection": store.collection,
        "points": store.count(),
        "documents": store.list_documents(),
        "embedder": store.embedder.name,
    }


class ChecklistSummary(BaseModel):
    id: str
    title: str
    n_items: int
    applies_to: list[str]
    scope_note: str | None


@server.tool(
    description="List available reporting / regulatory checklists (SPIRIT-AI, CONSORT-AI, STARD-AI, TRIPOD+AI, ISO 14155 CIP, TFDA, FDA CADe, IMDRF N41)."
)
def list_checklists() -> list[ChecklistSummary]:
    return [
        ChecklistSummary(
            id=c.id,
            title=c.title,
            n_items=len(c.items),
            applies_to=c.applies_to,
            scope_note=c.scope_note,
        )
        for c in ck.load_all().values()
    ]


@server.tool(
    description="Return the full item list of one checklist (ids, sections, text, keywords)."
)
def get_checklist(checklist_id: str) -> ck.Checklist:
    try:
        return ck.get_checklist(checklist_id)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc


@server.tool(
    description=(
        "Decide which checklists govern a study: design_type ∈ {Standalone_Performance, MRMC_Reader_Study, "
        "Hybrid_Standalone_and_MRMC, Prospective_Interventional_RCT}; samd_category e.g. CADe/CADx/CADt/"
        "Prognostic_Predictive; jurisdictions e.g. [TFDA, US_FDA_510k, CE_MDR]."
    )
)
def select_checklists(
    design_type: str,
    samd_category: str | None = None,
    jurisdictions: list[str] | None = None,
) -> list[ck.ChecklistSelection]:
    return ck.select_checklists(design_type, samd_category, jurisdictions)


class SectionsInput(BaseModel):
    sections: dict[str, str] = Field(description="Mapping of section name → draft text")


@server.tool(
    description=(
        "Deterministic keyword pre-screen of draft protocol sections against a checklist. Returns per-item "
        "status (likely_covered / weak / missing) with matched keywords and sections, to focus the LLM/human audit."
    )
)
def prescreen_checklist_coverage(checklist_id: str, sections: dict[str, str]) -> ck.CoverageReport:
    try:
        return ck.prescreen_coverage(checklist_id, sections)
    except KeyError as exc:
        raise ToolError(str(exc)) from exc
