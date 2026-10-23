"""In-process MCP round-trips (respx-mocked NCBI) plus opt-in live tests."""

import os

import pytest
from mcp.client.client import Client

from mcp_pubmed_evidence import server as srv
from mcp_pubmed_evidence.eutils import EUtilsClient
from mcp_pubmed_evidence.ratelimit import TokenBucket


async def _no_sleep(_: float) -> None:
    return None


@pytest.fixture(autouse=True)
def fast_factory():
    def factory() -> EUtilsClient:
        return EUtilsClient(
            api_key=None,
            email="dev@example.org",
            rate_limiter=TokenBucket(rate=1e9, capacity=10**6),
            sleep=_no_sleep,
        )

    srv.set_client_factory(factory)
    yield
    srv.set_client_factory(EUtilsClient)


@pytest.mark.anyio
async def test_tools_listed_with_schemas():
    async with Client(srv.server) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert names == {
            "search_baseline_performance",
            "search_ai_evidence",
            "fetch_abstract_citations",
            "extract_performance_metrics",
            "build_pubmed_query",
        }
        t = next(t for t in tools.tools if t.name == "search_baseline_performance")
        assert "disease" in t.input_schema["required"]
        assert t.output_schema is not None


@pytest.mark.anyio
async def test_search_baseline_round_trip(mocked_eutils):
    async with Client(srv.server) as client:
        result = await client.call_tool(
            "search_baseline_performance",
            {
                "disease": "intracranial hemorrhage",
                "modality": "head CT",
                "metric": "sensitivity",
                "max_results": 5,
            },
        )
    assert not result.is_error
    sc = result.structured_content
    assert sc["total_count"] == 2 and sc["returned"] == 2
    assert "NOT" in sc["query"] and '"intracranial hemorrhage"[tiab]' in sc["query"]
    first = sc["articles"][0]
    assert first["article"]["pmid"] == "31000001"
    metrics = {m["metric"]: m for m in first["extract"]["metrics"]}
    assert metrics["sensitivity"]["value"] == pytest.approx(0.884)
    assert metrics["sensitivity"]["ci_high"] == pytest.approx(0.912)
    assert first["extract"]["reader_count"] == 12
    assert "retrospective" in first["extract"]["design_keywords"]
    assert first["citation"].startswith("Smith JA, Lee K")
    assert first["url"].endswith("/31000001/")
    # the esearch request carried the generated term and the requested retmax
    req = mocked_eutils.get("esearch.fcgi").calls.last.request
    assert "retmax=5" in str(req.url)


@pytest.mark.anyio
async def test_search_ai_evidence_round_trip(mocked_eutils):
    async with Client(srv.server) as client:
        result = await client.call_tool(
            "search_ai_evidence", {"disease": "lung nodule", "modality": "CT"}
        )
    sc = result.structured_content
    assert not result.is_error
    assert '"deep learning"[tiab]' in sc["query"] and "NOT" not in sc["query"]


@pytest.mark.anyio
async def test_fetch_citations_reports_missing(mocked_eutils):
    async with Client(srv.server) as client:
        result = await client.call_tool(
            "fetch_abstract_citations",
            {"pmids": ["31000001", "31000002", "99999999"], "style": "apa"},
        )
    sc = result.structured_content
    assert sc["style"] == "apa" and len(sc["citations"]) == 2
    assert sc["citations"][0].startswith("Smith, J. A.")
    assert sc["missing_pmids"] == ["99999999"]


@pytest.mark.anyio
async def test_pure_tools_do_not_touch_network():
    async with Client(srv.server) as client:
        q = await client.call_tool(
            "build_pubmed_query",
            {
                "disease": "diabetic retinopathy",
                "modality": "fundus photography",
                "purpose": "ai_evidence",
            },
        )
        assert q.structured_content["purpose"] == "ai_evidence"
        ex = await client.call_tool(
            "extract_performance_metrics",
            {"text": "Sensitivity was 90% (95% CI 85-94) in 200 patients."},
        )
        sc = ex.structured_content
        assert sc["metrics"][0]["value"] == pytest.approx(0.90)
        assert sc["sample_sizes"][0]["n"] == 200


@pytest.mark.anyio
async def test_empty_pmids_is_tool_error():
    async with Client(srv.server) as client:
        result = await client.call_tool("fetch_abstract_citations", {"pmids": []})
        assert result.is_error


# ── live tests (run on the GB10 with LIVE_API_TESTS=1) ───────────────────────


@pytest.mark.live
@pytest.mark.anyio
async def test_live_search_baseline():
    srv.set_client_factory(lambda: EUtilsClient(api_key=os.environ.get("NCBI_API_KEY")))
    async with Client(srv.server) as client:
        result = await client.call_tool(
            "search_baseline_performance",
            {
                "disease": "intracranial hemorrhage",
                "modality": "computed tomography",
                "max_results": 3,
            },
        )
    assert not result.is_error
    assert result.structured_content["total_count"] > 0


@pytest.mark.live
@pytest.mark.anyio
async def test_live_fetch_citation():
    srv.set_client_factory(lambda: EUtilsClient(api_key=os.environ.get("NCBI_API_KEY")))
    async with Client(srv.server) as client:
        result = await client.call_tool(
            "fetch_abstract_citations", {"pmids": ["32856010"]}
        )  # Lancet Digit Health SPIRIT-AI
    assert not result.is_error and result.structured_content["citations"]
