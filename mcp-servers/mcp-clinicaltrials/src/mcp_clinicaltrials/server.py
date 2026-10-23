"""MCP tool surface for mcp-clinicaltrials (official MCP Python SDK 2.x, ``MCPServer``)."""

from __future__ import annotations

import asyncio
import os

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from . import analysis
from .client import CTGovClient, CTGovError
from .models import StudyProtocol, StudySummary, parse_study, to_summary

DEFAULT_AI_KEYWORDS = (
    "artificial intelligence OR deep learning OR machine learning OR computer-aided"
)

INSTRUCTIONS = """Search and read ClinicalTrials.gov (API v2) records of clinical studies, tuned for
AI/ML software-as-a-medical-device (AI-SaMD) protocol benchmarking.
Typical flow: search_samd_trials(condition=..., modality=...) → pick NCT ids →
get_trial_protocol_details / extract_eligibility_bullets for the design, eligibility and
endpoints → summarize_design_patterns(nct_ids) for an aggregate benchmark table.
Registry entries are self-reported by sponsors: treat endpoints, enrolment and designs as
reference points, not validated facts, and always cite the NCT id."""

server = MCPServer(
    name="mcp-clinicaltrials",
    title="ClinicalTrials.gov Explorer (AI-SaMD)",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)

_client: CTGovClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> CTGovClient:
    """Lazily create the shared HTTP client (base URL overridable via CTGOV_BASE_URL)."""
    global _client
    async with _client_lock:
        if _client is None:
            _client = CTGovClient(
                base_url=os.environ.get("CTGOV_BASE_URL", "https://clinicaltrials.gov/api/v2")
            )
        return _client


def set_client(client: CTGovClient | None) -> None:
    """Inject a client (tests)."""
    global _client
    _client = client


class SearchResult(BaseModel):
    total_count: int | None = Field(
        default=None, description="Total matching studies (countTotal=true)"
    )
    returned: int
    next_page_token: str | None = None
    query: dict[str, str | int | None]
    studies: list[StudySummary]


@server.tool(
    description=(
        "Search ClinicalTrials.gov for studies of AI/ML medical devices in a condition. "
        "Defaults the intervention query to AI-related keywords; add a modality (e.g. 'CT', 'chest X-ray', "
        "'ECG', 'fundus') to narrow. Returns compact study summaries with a pagination token."
    )
)
async def search_samd_trials(
    condition: str,
    intervention_keywords: str = DEFAULT_AI_KEYWORDS,
    modality: str | None = None,
    study_type: str | None = None,
    status: list[str] | None = None,
    page_size: int = 20,
    page_token: str | None = None,
) -> SearchResult:
    client = await get_client()
    try:
        raw = await client.search_studies(
            query_cond=condition,
            query_intr=intervention_keywords or None,
            query_term=modality,
            study_type=study_type,
            status=status,
            page_size=page_size,
            page_token=page_token,
        )
    except CTGovError as exc:
        raise ValueError(str(exc)) from exc
    studies = [to_summary(parse_study(s)) for s in raw.get("studies", [])]
    return SearchResult(
        total_count=raw.get("totalCount"),
        returned=len(studies),
        next_page_token=raw.get("nextPageToken"),
        query={
            "condition": condition,
            "intervention_keywords": intervention_keywords,
            "modality": modality,
            "study_type": study_type,
            "status": ",".join(status) if status else None,
            "page_size": page_size,
        },
        studies=studies,
    )


@server.tool(
    description=(
        "Full normalised protocol for one NCT id: design, arms/interventions, eligibility, primary & "
        "secondary outcomes, enrolment, sponsor, sites and references."
    )
)
async def get_trial_protocol_details(nct_id: str) -> StudyProtocol:
    client = await get_client()
    try:
        return parse_study(await client.get_study(nct_id))
    except CTGovError as exc:
        raise ValueError(str(exc)) from exc


class EligibilityBulletsResult(analysis.EligibilityBullets):
    nct_id: str
    sex: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    std_ages: list[str] = Field(default_factory=list)


@server.tool(
    description="Inclusion / exclusion criteria of one study split into bullet lists, plus age/sex limits."
)
async def extract_eligibility_bullets(nct_id: str) -> EligibilityBulletsResult:
    client = await get_client()
    try:
        proto = parse_study(await client.get_study(nct_id))
    except CTGovError as exc:
        raise ValueError(str(exc)) from exc
    bullets = analysis.extract_eligibility_bullets(proto.eligibility.criteria)
    return EligibilityBulletsResult(
        nct_id=proto.nct_id,
        inclusion=bullets.inclusion,
        exclusion=bullets.exclusion,
        unclassified=bullets.unclassified,
        sex=proto.eligibility.sex,
        minimum_age=proto.eligibility.minimum_age,
        maximum_age=proto.eligibility.maximum_age,
        std_ages=proto.eligibility.std_ages,
    )


@server.tool(
    description=(
        "Aggregate design statistics across several NCT ids (study types, time perspective, enrolment "
        "median/IQR, endpoint keyword frequency, age limits) — the Predicate Benchmark Matrix input."
    )
)
async def summarize_design_patterns(nct_ids: list[str]) -> analysis.DesignPatternSummary:
    if not nct_ids:
        raise ValueError("nct_ids must not be empty")
    if len(nct_ids) > 50:
        raise ValueError("at most 50 NCT ids per call")
    client = await get_client()

    async def fetch(nct: str) -> StudyProtocol | Exception:
        try:
            return parse_study(await client.get_study(nct))
        except CTGovError as exc:
            return exc

    results = await asyncio.gather(*(fetch(n) for n in nct_ids))
    studies = [r for r in results if isinstance(r, StudyProtocol)]
    failed = [n for n, r in zip(nct_ids, results, strict=True) if isinstance(r, Exception)]
    summary = analysis.summarize_design_patterns(studies)
    if failed:
        summary.notes.append(f"Could not retrieve: {', '.join(failed)}")
    return summary
