from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.db import Database
from app.llm.fake import FakeLLM
from app.main import create_app
from app.mcp_client.fake import FakeTarget
from app.mcp_client.manager import ClientTarget, McpManager
from app.schemas.protocol_input import EXAMPLE_INPUT


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def canned_targets() -> dict:
    """Realistic canned outputs for the three external-API servers (shapes match the real MCP servers)."""
    trials = {
        "total_count": 2,
        "returned": 2,
        "next_page_token": None,
        "query": {"condition": "Acute intracranial hemorrhage"},
        "studies": [
            {
                "nct_id": "NCT06018545",
                "brief_title": "AI Assisted Reader Evaluation in Acute CT Head Interpretation",
                "overall_status": "COMPLETED",
                "study_type": "OBSERVATIONAL",
                "design_info": {
                    "observational_model": "COHORT",
                    "time_perspective": "RETROSPECTIVE",
                },
                "enrollment": {"count": 33, "type": "ACTUAL"},
                "conditions": ["Intracranial Hemorrhage"],
                "primary_outcomes": [
                    {"measure": "Reader sensitivity and specificity with vs without AI"}
                ],
                "lead_sponsor": "Example University",
                "countries": ["United Kingdom"],
                "url": "https://clinicaltrials.gov/study/NCT06018545",
            },
            {
                "nct_id": "NCT00000002",
                "brief_title": "Prospective triage of ICH with deep learning",
                "overall_status": "RECRUITING",
                "study_type": "INTERVENTIONAL",
                "design_info": {"allocation": "RANDOMIZED", "masking": "NONE"},
                "enrollment": {"count": 1200, "type": "ESTIMATED"},
                "conditions": ["Intracranial Hemorrhage"],
                "primary_outcomes": [{"measure": "Time to notification"}],
            },
        ],
    }
    bench = {
        "devices": [
            {
                "submission_number": "K180647",
                "summary_url": "https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180647.pdf",
                "pdf_found": True,
                "http_status": 200,
                "extract": {
                    "section_excerpts": [
                        "Standalone performance testing was conducted on 500 non-contrast head CT cases from 3 US sites."
                    ],
                    "metrics": [
                        {
                            "metric": "sensitivity",
                            "value": 0.935,
                            "ci_lower": 0.912,
                            "ci_upper": 0.951,
                            "context": "sensitivity of 93.5%",
                        },
                        {
                            "metric": "specificity",
                            "value": 0.890,
                            "ci_lower": 0.86,
                            "ci_upper": 0.91,
                            "context": "specificity of 89.0%",
                        },
                    ],
                    "n_cases": 500,
                    "n_readers": None,
                    "ground_truth_sentences": [
                        "Reference standard established by consensus of three neuroradiologists."
                    ],
                    "design_keywords": ["retrospective", "multicenter", "standalone"],
                    "predicate_k_numbers": ["K173542"],
                    "confidence": "high",
                },
            }
        ],
        "aggregate": {
            "devices_requested": 1,
            "devices_with_summary": 1,
            "median_cases": 500,
            "sensitivity_range": [0.935, 0.935],
            "specificity_range": [0.89, 0.89],
        },
        "notes": [],
    }
    found = {
        "query": "product_code:QAS",
        "meta": {"total": 2},
        "devices": [
            {
                "k_number": "K180647",
                "device_name": "Example ICH Triage",
                "applicant": "Example Inc",
                "decision_date": "2018-08-01",
                "product_code": "QAS",
                "summary_pdf_url": "https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180647.pdf",
            },
            {
                "k_number": "K193456",
                "device_name": "Other ICH CADt",
                "applicant": "Other Co",
                "decision_date": "2020-01-15",
                "product_code": "QAS",
            },
        ],
    }
    ai_list = {
        "total_in_list": 1614,
        "matched": 1,
        "returned": 1,
        "source_url": "https://www.fda.gov/media/178541/download?attachment",
        "devices": [
            {
                "decision_date": "2021-03-01",
                "submission_number": "K203456",
                "device_name": "ICH Detect",
                "company": "Co",
                "panel": "Radiology",
                "product_code": "QAS",
                "submission_type": "510k",
            }
        ],
    }
    pubmed_base = {
        "query": "(intracranial hemorrhage[tiab]) AND (sensitivity[tiab]) NOT (deep learning[tiab])",
        "total_count": 1,
        "returned": 1,
        "articles": [
            {
                "article": {
                    "pmid": "31234567",
                    "title": "Diagnostic accuracy of emergency physicians for ICH on head CT",
                    "year": 2019,
                    "journal": "Emerg Radiol",
                },
                "extract": {
                    "metrics": [
                        {
                            "metric": "sensitivity",
                            "value": 0.84,
                            "ci_low": 0.80,
                            "ci_high": 0.88,
                            "as_reported": "84%",
                            "context": "sensitivity 84%",
                        },
                        {
                            "metric": "specificity",
                            "value": 0.95,
                            "as_reported": "95%",
                            "context": "specificity 95%",
                        },
                    ],
                    "sample_sizes": [{"n": 1250, "unit": "scans", "context": "1250 head CT scans"}],
                    "reader_count": 3,
                    "design_keywords": ["retrospective"],
                    "has_ai_terms": False,
                },
                "citation": "Smith J, et al. Diagnostic accuracy of emergency physicians for ICH on head CT. Emerg Radiol. 2019;26(3):123-30.",
                "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/",
            }
        ],
        "notes": [],
    }
    pubmed_ai = {"query": "ai", "total_count": 0, "returned": 0, "articles": [], "notes": []}
    return {
        "clinicaltrials": FakeTarget("clinicaltrials", {"search_samd_trials": trials}),
        "openfda": FakeTarget(
            "openfda",
            {
                "summarize_predicate_benchmarks": bench,
                "find_predicate_devices": found,
                "search_fda_ai_device_list": ai_list,
            },
        ),
        "pubmed": FakeTarget(
            "pubmed", {"search_baseline_performance": pubmed_base, "search_ai_evidence": pubmed_ai}
        ),
    }


def make_mcp() -> McpManager:
    from qdrant_client import QdrantClient

    from mcp_biostat_calc.server import server as bio
    from mcp_regulatory_rag import server as rag_mod
    from mcp_regulatory_rag.embeddings import HashingEmbedder
    from mcp_regulatory_rag.ingest import checklist_chunks
    from mcp_regulatory_rag.store import GuidanceStore

    store = GuidanceStore(QdrantClient(":memory:"), HashingEmbedder(dim=64), collection="t")
    store.ensure_collection(recreate=True)
    store.upsert_chunks(checklist_chunks())
    rag_mod.set_store(store)
    targets: dict = canned_targets()
    targets["biostat"] = ClientTarget(bio, name="biostat")
    targets["regulatory_rag"] = ClientTarget(rag_mod.server, name="regulatory_rag")
    return McpManager(targets)


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
async def app(tmp_path, fake_llm):
    settings = Settings(
        llm_provider="fake",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db",
        max_audit_iterations=2,
        writer_concurrency=4,
    )
    db = Database(settings.database_url)
    await db.init()
    application = create_app(settings, llm=fake_llm, mcp=make_mcp(), database=db)
    yield application
    await application.state.manager.shutdown()
    await db.close()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def example_input() -> dict:
    return EXAMPLE_INPUT
