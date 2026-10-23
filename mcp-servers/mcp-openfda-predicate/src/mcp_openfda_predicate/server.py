"""MCP tool surface for mcp-openfda-predicate (official MCP Python SDK 2.x, ``MCPServer``)."""

from __future__ import annotations

import asyncio
import os

import httpx
from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from . import ai_list, openfda, pdfs

INSTRUCTIONS = """FDA predicate-device evidence for AI-SaMD protocol drafting.
Workflow: (1) search_fda_ai_device_list or find_predicate_devices to locate cleared devices with the
same product code / indication; (2) extract_510k_clinical_summary (or extract_denovo_clinical_summary)
to pull the clinical-validation design actually accepted by FDA: test-set size, readers, ground truth,
sensitivity/specificity/AUC, performance goals; (3) summarize_predicate_benchmarks to build the
Predicate Benchmark Matrix across several K-numbers.
Caveats: openFDA covers 510(k) only (no De Novo endpoint); many devices file a 510(k) *statement*
(no public summary → pdf_found=false); extracted numbers are regex heuristics and must be verified
against the cited PDF before use in a protocol."""

server = MCPServer(
    name="mcp-openfda-predicate",
    title="openFDA Predicate Device Evidence",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)

_ai_cache = ai_list.AIDeviceListCache()


def _openfda_base_url() -> str:
    return os.environ.get("OPENFDA_BASE_URL", openfda.OPENFDA_BASE_URL)


def _accessdata_base_url() -> str:
    return os.environ.get("ACCESSDATA_BASE_URL", pdfs.ACCESSDATA_BASE_URL)


class SummaryResult(BaseModel):
    submission_number: str
    summary_url: str
    pdf_found: bool
    http_status: int
    extract: pdfs.ClinicalSummaryExtract | None = None
    error: str | None = None


class BenchmarkMatrix(BaseModel):
    devices: list[SummaryResult]
    aggregate: pdfs.BenchmarkAggregate
    notes: list[str] = Field(default_factory=list)


class AIDeviceListResult(BaseModel):
    total_in_list: int
    matched: int
    returned: int
    devices: list[ai_list.AIDeviceRow]
    source_url: str


async def _extract_from_url(submission_number: str, url: str) -> SummaryResult:
    fetched = await pdfs.fetch_pdf_text(url)
    if not fetched.found:
        return SummaryResult(
            submission_number=submission_number,
            summary_url=url,
            pdf_found=False,
            http_status=fetched.status_code,
            error=fetched.error
            or ("no public summary PDF at this URL (404)" if fetched.status_code == 404 else None),
        )
    if fetched.error:
        return SummaryResult(
            submission_number=submission_number,
            summary_url=url,
            pdf_found=True,
            http_status=fetched.status_code,
            error=fetched.error,
        )
    extract = pdfs.extract_clinical_summary(
        fetched.text, source_url=url, pages=fetched.pages, own_k_number=submission_number
    )
    if fetched.truncated:
        extract.notes.append(
            f"PDF has {fetched.pages} pages; only the first {pdfs.MAX_PDF_PAGES} were read."
        )
    return SummaryResult(
        submission_number=submission_number,
        summary_url=url,
        pdf_found=True,
        http_status=fetched.status_code,
        extract=extract,
    )


@server.tool(
    description=(
        "Search openFDA 510(k) clearances for candidate predicate devices by product code "
        "(e.g. QAS, QIH, QFM, LLZ), device-name keyword, applicant and decision-date range. "
        "Returns up to 100 records per page with the derived summary PDF URL."
    )
)
async def find_predicate_devices(
    product_code: str | None = None,
    keyword: str | None = None,
    applicant: str | None = None,
    decision_date_from: str | None = None,
    decision_date_to: str | None = None,
    limit: int = 20,
    skip: int = 0,
) -> openfda.Search510kResult:
    query = openfda.build_510k_query(
        product_code=product_code,
        keyword=keyword,
        applicant=applicant,
        decision_date_from=decision_date_from,
        decision_date_to=decision_date_to,
    )
    async with openfda.OpenFDAClient(base_url=_openfda_base_url()) as client:
        return await client.search_510k(query, limit=limit, skip=skip)


@server.tool(description="Fetch one openFDA 510(k) record by K-number (e.g. K183285).")
async def get_510k_record(k_number: str) -> openfda.Device510k | None:
    k = pdfs.normalise_k_number(k_number)
    async with openfda.OpenFDAClient(base_url=_openfda_base_url()) as client:
        return await client.get_510k(k)


@server.tool(
    description=(
        "Download the public 510(k) summary PDF for a K-number from accessdata.fda.gov and extract "
        "clinical-validation facts (test-set size, readers, sites, ground truth, sensitivity/specificity/AUC, "
        "performance goals, design keywords, cited predicates). pdf_found=false when FDA has no summary on file."
    )
)
async def extract_510k_clinical_summary(k_number: str) -> SummaryResult:
    k = pdfs.normalise_k_number(k_number)
    return await _extract_from_url(
        k, pdfs.k_number_to_summary_url(k, base_url=_accessdata_base_url())
    )


@server.tool(
    description=(
        "Download the De Novo decision summary PDF (DENxxxxxx) from accessdata.fda.gov/cdrh_docs/reviews "
        "and extract clinical-validation facts and special controls language."
    )
)
async def extract_denovo_clinical_summary(den_number: str) -> SummaryResult:
    url = pdfs.den_number_to_summary_url(den_number, base_url=_accessdata_base_url())
    den = den_number.strip().upper()
    return await _extract_from_url(den, url)


@server.tool(
    description=(
        "Search FDA's published 'Artificial Intelligence-Enabled Medical Devices' list (CSV; ~1,600 "
        "510(k)/De Novo/PMA authorisations) by keyword, product code, lead review panel and decision year."
    )
)
async def search_fda_ai_device_list(
    keyword: str | None = None,
    product_code: str | None = None,
    panel: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    submission_type: str | None = None,
    limit: int = 50,
) -> AIDeviceListResult:
    rows = await _ai_cache.rows()
    matched = ai_list.filter_rows(
        rows,
        keyword=keyword,
        product_code=product_code,
        panel=panel,
        year_from=year_from,
        year_to=year_to,
        submission_type=submission_type,
    )
    limit = max(1, min(int(limit), 500))
    return AIDeviceListResult(
        total_in_list=len(rows),
        matched=len(matched),
        returned=min(limit, len(matched)),
        devices=matched[:limit],
        source_url=_ai_cache.url,
    )


@server.tool(
    description=(
        "Build a Predicate Benchmark Matrix: fetch and extract the 510(k) summaries (K…) or De Novo "
        "summaries (DEN…) for several submission numbers and aggregate cases, readers and reported "
        "sensitivity/specificity/AUC ranges. Fetches run concurrently (max 4 at a time)."
    )
)
async def summarize_predicate_benchmarks(submission_numbers: list[str]) -> BenchmarkMatrix:
    if not submission_numbers:
        raise ValueError("submission_numbers must not be empty")
    if len(submission_numbers) > 25:
        raise ValueError("at most 25 submissions per call")
    sem = asyncio.Semaphore(4)

    async def one(sub: str) -> SummaryResult:
        s = sub.strip().upper()
        try:
            url = (
                pdfs.den_number_to_summary_url(s, base_url=_accessdata_base_url())
                if s.startswith("DEN")
                else pdfs.k_number_to_summary_url(s, base_url=_accessdata_base_url())
            )
        except ValueError as exc:
            return SummaryResult(
                submission_number=s, summary_url="", pdf_found=False, http_status=0, error=str(exc)
            )
        async with sem:
            try:
                return await _extract_from_url(s, url)
            except httpx.HTTPError as exc:  # pragma: no cover - network failure path
                return SummaryResult(
                    submission_number=s,
                    summary_url=url,
                    pdf_found=False,
                    http_status=0,
                    error=str(exc),
                )

    results = list(await asyncio.gather(*(one(s) for s in submission_numbers)))
    extracts = [
        r.extract if r.extract is not None else pdfs.ClinicalSummaryExtract(pdf_found=False)
        for r in results
    ]
    agg = pdfs.aggregate_benchmarks(extracts)
    notes = [
        "Aggregate statistics only cover devices whose summary PDF was found and parsed.",
        "Numbers are heuristic extractions; cite and verify the source PDF for each row.",
    ]
    return BenchmarkMatrix(devices=results, aggregate=agg, notes=notes)
