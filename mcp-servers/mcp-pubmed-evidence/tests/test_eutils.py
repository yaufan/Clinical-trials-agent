import httpx
import pytest
import respx

from mcp_pubmed_evidence.eutils import EUtilsClient, EUtilsError, parse_pubmed_xml
from mcp_pubmed_evidence.ratelimit import TokenBucket

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


async def _no_sleep(_: float) -> None:
    return None


def _fast_client(**kw) -> EUtilsClient:
    bucket = TokenBucket(rate=1e9, capacity=1_000_000)
    return EUtilsClient(
        api_key=kw.pop("api_key", None),
        email="dev@example.org",
        rate_limiter=bucket,
        sleep=_no_sleep,
        **kw,
    )


def test_parse_xml_fixture(efetch_xml):
    arts = parse_pubmed_xml(efetch_xml)
    assert [a.pmid for a in arts] == ["31000001", "31000002"]
    a = arts[0]
    assert a.title.startswith("Diagnostic Performance of Radiologists") and a.title.endswith(
        "Reader Study"
    )
    assert "CT" in a.title  # inline <i> flattened
    assert a.abstract.startswith("BACKGROUND: Missed intracranial hemorrhage")
    assert "RESULTS: Pooled reader sensitivity was 88.4%" in a.abstract
    assert a.journal == "Radiology" and a.journal_abbreviation == "Radiology"
    assert (a.year, a.volume, a.issue, a.pages) == (2021, "298", "2", "345-53")
    assert a.authors[:2] == ["Smith JA", "Lee K"] and len(a.authors) == 7
    assert a.doi == "10.1148/radiol.2021000001" and a.pmc_id == "PMC7000001"
    assert "Intracranial Hemorrhages" in a.mesh_terms
    assert "Multicenter Study" in a.publication_types
    b = arts[1]
    assert b.year == 2019  # MedlineDate fallback
    assert b.authors == ["Brown A", "ED Imaging Group"]
    assert b.doi is None and b.issue == ""


@pytest.mark.anyio
async def test_esearch_parses_and_sends_identification(mocked_eutils):
    async with _fast_client(api_key="KEY123") as client:
        res = await client.esearch("test query", retmax=5)
    assert res.count == 2 and res.pmids == ["31000001", "31000002"]
    assert res.query_translation.startswith('"intracranial')
    req = mocked_eutils.get("esearch.fcgi").calls.last.request
    params = dict(httpx.QueryParams(req.url.query))
    assert params["db"] == "pubmed" and params["retmode"] == "json"
    assert params["term"] == "test query" and params["retmax"] == "5"
    assert params["api_key"] == "KEY123" and params["email"] == "dev@example.org"
    assert params["tool"]


@pytest.mark.anyio
async def test_esummary_and_efetch(mocked_eutils):
    async with _fast_client() as client:
        summ = await client.esummary(["31000001"])
        full = await client.efetch_abstracts(["31000001", "31000002"])
    assert summ[0].doi == "10.1148/radiol.2021000001" and summ[0].year == 2021
    assert summ[0].title.endswith("Hemorrhage")
    assert len(full) == 2 and full[0].abstract
    assert await _fast_client().esummary([]) == []


@pytest.mark.anyio
async def test_retries_on_429_then_succeeds(esearch_json):
    with respx.mock(base_url=BASE) as router:
        route = router.get("esearch.fcgi").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(503),
                httpx.Response(200, json=esearch_json),
            ]
        )
        async with _fast_client() as client:
            res = await client.esearch("x")
        assert res.count == 2
        assert route.call_count == 3


@pytest.mark.anyio
async def test_gives_up_after_max_retries():
    with respx.mock(base_url=BASE) as router:
        router.get("esearch.fcgi").mock(return_value=httpx.Response(500))
        async with _fast_client(max_retries=2) as client:
            with pytest.raises(EUtilsError):
                await client.esearch("x")


@pytest.mark.anyio
async def test_esearch_error_payload():
    with respx.mock(base_url=BASE) as router:
        router.get("esearch.fcgi").mock(
            return_value=httpx.Response(
                200, json={"esearchresult": {"ERROR": "Empty term and query_key"}}
            )
        )
        async with _fast_client() as client:
            with pytest.raises(EUtilsError):
                await client.esearch("")


def test_rate_defaults_follow_api_key():
    assert _fast_client().api_key in (None, "") or True  # construction must not fail
    assert EUtilsClient(api_key=None, email=None)._bucket.rate == 3.0
    assert EUtilsClient(api_key="k", email=None)._bucket.rate == 10.0
