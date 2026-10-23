"""MCP tool surface for mcp-pubmed-evidence (official MCP Python SDK 2.x, ``MCPServer``)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from mcp.server.mcpserver import MCPServer

from .citations import format_citation
from .eutils import EUtilsClient
from .extract import extract_performance
from .models import (
    ArticleWithEvidence,
    CitationsResponse,
    PerformanceExtract,
    PubMedArticle,
    QueryResponse,
    SearchResponse,
)
from .queries import build_ai_evidence_query, build_baseline_query

INSTRUCTIONS = """PubMed evidence retrieval (NCBI E-utilities) for AI-SaMD clinical protocols.
- search_baseline_performance finds how UNAIDED clinicians perform on the target task
  (AI papers excluded) — use the extracted sensitivity/specificity/AUC values as the
  literature baseline for performance goals and sample-size assumptions.
- search_ai_evidence finds prior AI/ML studies on the same task for the literature review.
- Every search returns the exact PubMed query string; use build_pubmed_query first if you want to
  inspect or refine it. Extracted numbers are regex-based: always quote `context` and cite PMIDs.
- fetch_abstract_citations returns Vancouver/APA references for a list of PMIDs."""

server = MCPServer(
    name="mcp-pubmed-evidence",
    title="PubMed Evidence (AI-SaMD)",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)

# Factory indirection lets tests inject a client bound to a mocked transport.
_client_factory: Callable[[], EUtilsClient] = EUtilsClient


def set_client_factory(factory: Callable[[], EUtilsClient]) -> None:
    global _client_factory
    _client_factory = factory


def _with_evidence(article: PubMedArticle, style: str) -> ArticleWithEvidence:
    text = f"{article.title}. {article.abstract}" if article.abstract else article.title
    return ArticleWithEvidence(
        article=article,
        extract=extract_performance(text),
        citation=format_citation(article, style),
        url=article.url,
    )


async def _run_search(
    query: QueryResponse, max_results: int, sort: str, notes: list[str]
) -> SearchResponse:
    max_results = max(1, min(int(max_results), 100))
    async with _client_factory() as client:
        search, articles = await client.search_and_fetch(query.query, retmax=max_results, sort=sort)
    enriched = [_with_evidence(a, "vancouver") for a in articles]
    if search.count == 0:
        notes.append("No results: broaden the disease/modality terms or drop the metric filter.")
    return SearchResponse(
        query=query.query,
        query_translation=search.query_translation,
        total_count=search.count,
        returned=len(enriched),
        articles=enriched,
        notes=notes,
    )


@server.tool(
    description=(
        "Search PubMed for UNAIDED clinician baseline diagnostic performance (sensitivity, "
        "specificity, AUC…) on a disease/modality, excluding AI papers by default. Returns articles "
        "with regex-extracted metrics + CIs, sample sizes, reader counts and Vancouver citations."
    )
)
async def search_baseline_performance(
    disease: str,
    modality: str | None = None,
    metric: str | None = None,
    years_back: int = 10,
    max_results: int = 20,
    exclude_ai: bool = True,
    sort: Literal["relevance", "pub_date"] = "relevance",
) -> SearchResponse:
    q = build_baseline_query(disease, modality, metric, exclude_ai=exclude_ai, years=years_back)
    notes = [
        "Baseline query targets human-reader performance; verify each extracted value against the quoted context.",
    ]
    return await _run_search(q, max_results, sort, notes)


@server.tool(
    description=(
        "Search PubMed for prior AI/ML studies on the same disease/modality (predicate-style "
        "evidence for the literature review). Same output shape as search_baseline_performance."
    )
)
async def search_ai_evidence(
    disease: str,
    modality: str | None = None,
    metric: str | None = None,
    years_back: int = 10,
    max_results: int = 20,
    sort: Literal["relevance", "pub_date"] = "relevance",
) -> SearchResponse:
    q = build_ai_evidence_query(disease, modality, metric, years=years_back)
    notes = ["AI-inclusive query; `extract.has_ai_terms` flags abstracts mentioning AI/ML."]
    return await _run_search(q, max_results, sort, notes)


@server.tool(
    description="Fetch full PubMed records for a list of PMIDs and format them as Vancouver or APA references."
)
async def fetch_abstract_citations(
    pmids: list[str],
    style: Literal["vancouver", "apa"] = "vancouver",
) -> CitationsResponse:
    clean = [str(p).strip() for p in pmids if str(p).strip()]
    if not clean:
        raise ValueError("pmids must contain at least one PMID")
    async with _client_factory() as client:
        articles = await client.efetch_abstracts(clean)
    found = {a.pmid for a in articles}
    return CitationsResponse(
        style=style,
        articles=articles,
        citations=[format_citation(a, style) for a in articles],
        missing_pmids=[p for p in clean if p not in found],
    )


@server.tool(
    description=(
        "Deterministically extract sensitivity/specificity/AUC/accuracy/PPV/NPV values (with 95% CIs), "
        "sample sizes, reader counts and study-design keywords from any abstract text."
    )
)
def extract_performance_metrics(text: str) -> PerformanceExtract:
    return extract_performance(text)


@server.tool(
    description=(
        "Build (without executing) the PubMed query string used by the search tools, so it can be "
        "inspected or edited. purpose='baseline_unaided' excludes AI papers; 'ai_evidence' requires them."
    )
)
def build_pubmed_query(
    disease: str,
    modality: str | None = None,
    metric: str | None = None,
    purpose: Literal["baseline_unaided", "ai_evidence"] = "baseline_unaided",
    years_back: int | None = 10,
    humans_only: bool = True,
) -> QueryResponse:
    if purpose == "ai_evidence":
        return build_ai_evidence_query(
            disease, modality, metric, years=years_back, humans_only=humans_only
        )
    return build_baseline_query(
        disease, modality, metric, years=years_back, humans_only=humans_only
    )
