import os

import httpx
import pytest
import respx
from mcp.client.client import Client

from mcp_clinicaltrials import server as srv
from mcp_clinicaltrials.client import CTGovClient, CTGovError

BASE = "https://ctgov.test/api/v2"


@pytest.fixture
def mock_api(study_fixture, search_fixture):
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        mock.get("/studies/NCT06018545").mock(return_value=httpx.Response(200, json=study_fixture))
        mock.get("/studies/NCT06242938").mock(
            return_value=httpx.Response(200, json=search_fixture["studies"][1])
        )
        mock.get("/studies/NCT00000404").mock(
            return_value=httpx.Response(404, json={"message": "not found"})
        )
        mock.get("/studies").mock(return_value=httpx.Response(200, json=search_fixture))
        yield mock


@pytest.fixture
def client(mock_api):
    c = CTGovClient(base_url=BASE, backoff_seconds=0.0)
    srv.set_client(c)
    yield c
    srv.set_client(None)


@pytest.mark.anyio
async def test_search_passes_filters_and_pagination(client, mock_api):
    raw = await client.search_studies(
        query_cond="intracranial hemorrhage",
        query_intr="deep learning",
        query_term="CT",
        study_type="observational",
        status=["completed", "recruiting"],
        page_size=5,
        page_token="TOKEN123",
        fields=["NCTId", "BriefTitle"],
    )
    assert raw["totalCount"] == 18 and raw["nextPageToken"]
    req = mock_api.get("/studies").calls.last.request
    q = dict(httpx.QueryParams(req.url.query))
    assert q["query.cond"] == "intracranial hemorrhage"
    assert q["query.intr"] == "deep learning"
    assert q["query.term"] == "CT"
    assert q["filter.advanced"] == "AREA[StudyType]OBSERVATIONAL"
    assert q["filter.overallStatus"] == "COMPLETED,RECRUITING"
    assert q["pageToken"] == "TOKEN123"
    assert q["pageSize"] == "5"
    assert q["fields"] == "NCTId,BriefTitle"
    assert q["countTotal"] == "true" and q["format"] == "json"


@pytest.mark.anyio
async def test_retry_on_500_then_success(mock_api, study_fixture):
    route = mock_api.get("/studies/NCT06018545")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(503),
        httpx.Response(200, json=study_fixture),
    ]
    c = CTGovClient(base_url=BASE, backoff_seconds=0.0, max_retries=3)
    data = await c.get_study("nct06018545")
    assert data["protocolSection"]["identificationModule"]["nctId"] == "NCT06018545"
    assert route.call_count == 3
    await c.aclose()


@pytest.mark.anyio
async def test_retries_exhausted_raises(mock_api):
    mock_api.get("/studies/NCT06018545").mock(return_value=httpx.Response(502))
    c = CTGovClient(base_url=BASE, backoff_seconds=0.0, max_retries=2)
    with pytest.raises(CTGovError, match="giving up"):
        await c.get_study("NCT06018545")
    await c.aclose()


@pytest.mark.anyio
async def test_404_and_invalid_id(client):
    with pytest.raises(CTGovError, match="not found"):
        await client.get_study("NCT00000404")
    with pytest.raises(CTGovError, match="invalid NCT id"):
        await client.get_study("ABC123")


@pytest.mark.anyio
async def test_server_tools_listed():
    async with Client(srv.server) as mcp:
        tools = {t.name: t for t in (await mcp.list_tools()).tools}
        assert set(tools) == {
            "search_samd_trials",
            "get_trial_protocol_details",
            "extract_eligibility_bullets",
            "summarize_design_patterns",
        }
        assert "condition" in tools["search_samd_trials"].input_schema["required"]
        assert tools["get_trial_protocol_details"].output_schema is not None


@pytest.mark.anyio
async def test_server_search_round_trip(client):
    async with Client(srv.server) as mcp:
        res = await mcp.call_tool(
            "search_samd_trials", {"condition": "intracranial hemorrhage", "modality": "CT"}
        )
        assert not res.is_error
        sc = res.structured_content
        assert sc["total_count"] == 18 and sc["returned"] == 2
        assert sc["next_page_token"]
        assert sc["studies"][0]["nct_id"] == "NCT06018545"
        assert sc["query"]["modality"] == "CT"


@pytest.mark.anyio
async def test_server_details_eligibility_and_summary(client):
    async with Client(srv.server) as mcp:
        det = await mcp.call_tool("get_trial_protocol_details", {"nct_id": "NCT06018545"})
        assert det.structured_content["eligibility"]["sex"] == "ALL"
        assert len(det.structured_content["arms"]) == 2

        elig = await mcp.call_tool("extract_eligibility_bullets", {"nct_id": "NCT06018545"})
        assert elig.structured_content["exclusion"][0] == "Neuroradiologists."

        summ = await mcp.call_tool(
            "summarize_design_patterns", {"nct_ids": ["NCT06018545", "NCT06242938", "NCT00000404"]}
        )
        sc = summ.structured_content
        assert sc["n_studies"] == 2
        assert sc["study_types"] == {"OBSERVATIONAL": 1, "INTERVENTIONAL": 1}
        assert any("NCT00000404" in n for n in sc["notes"])


@pytest.mark.anyio
async def test_server_errors_surface_as_tool_errors(client):
    async with Client(srv.server) as mcp:
        res = await mcp.call_tool("get_trial_protocol_details", {"nct_id": "NCT00000404"})
        assert res.is_error
        res = await mcp.call_tool("summarize_design_patterns", {"nct_ids": []})
        assert res.is_error


@pytest.mark.live
@pytest.mark.skipif(
    os.environ.get("LIVE_API_TESTS") != "1", reason="set LIVE_API_TESTS=1 to hit clinicaltrials.gov"
)
@pytest.mark.anyio
async def test_live_search_and_fetch():
    c = CTGovClient()
    try:
        raw = await c.search_studies(
            query_cond="intracranial hemorrhage", query_intr="artificial intelligence", page_size=3
        )
        assert raw["totalCount"] >= 1 and raw["studies"]
        nct = raw["studies"][0]["protocolSection"]["identificationModule"]["nctId"]
        study = await c.get_study(nct)
        assert study["protocolSection"]["identificationModule"]["nctId"] == nct
    finally:
        await c.aclose()
