import json
from pathlib import Path

import httpx
import pytest

from mcp_openfda_predicate import openfda

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openfda_510k_qas.json").read_text())
BASE = "https://api.fda.gov"


def test_keyword_clause_forms():
    assert (
        openfda.keyword_clause("device_name", "intracranial hemorrhage")
        == "device_name:(intracranial+hemorrhage)"
    )
    assert openfda.keyword_clause("device_name", "triage") == "device_name:triage"
    with pytest.raises(ValueError):
        openfda.keyword_clause("device_name", "   ")


def test_build_query_combines_clauses():
    q = openfda.build_510k_query(
        product_code="qas", keyword="computer aided", decision_date_from="2020-01-01"
    )
    assert (
        q
        == "product_code:QAS+AND+device_name:(computer+aided)+AND+decision_date:[2020-01-01+TO+2099-12-31]"
    )
    with pytest.raises(ValueError):
        openfda.build_510k_query()
    with pytest.raises(ValueError):
        openfda.build_510k_query(decision_date_from="01/01/2020")


@pytest.mark.anyio
async def test_search_510k_parses_records(respx_mock):
    route = respx_mock.get(url__startswith=f"{BASE}/device/510k.json").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    async with openfda.OpenFDAClient(base_url=BASE, api_key="") as client:
        res = await client.search_510k(openfda.build_510k_query(product_code="QAS"), limit=2)
    assert route.called
    sent = str(route.calls.last.request.url)
    assert "search=product_code:QAS&limit=2&skip=0" in sent and "api_key" not in sent
    assert res.meta.total == 89
    assert [d.k_number for d in res.devices] == ["K253163", "K260729"]
    d = res.devices[0]
    assert d.product_code == "QAS" and d.device_class == "2" and d.regulation_number == "892.2080"
    assert d.generic_device_name.startswith("Radiological Computer-Assisted Triage")
    assert d.summary_pdf_url == "https://www.accessdata.fda.gov/cdrh_docs/pdf25/K253163.pdf"


@pytest.mark.anyio
async def test_search_510k_no_matches_returns_empty(respx_mock):
    respx_mock.get(url__startswith=f"{BASE}/device/510k.json").mock(
        return_value=httpx.Response(
            404, json={"error": {"code": "NOT_FOUND", "message": "No matches found!"}}
        )
    )
    async with openfda.OpenFDAClient(base_url=BASE, api_key="") as client:
        res = await client.search_510k("product_code:ZZZZ9")
    assert res.devices == [] and res.meta.total == 0


@pytest.mark.anyio
async def test_search_510k_retries_on_429_then_succeeds(respx_mock):
    route = respx_mock.get(url__startswith=f"{BASE}/device/510k.json").mock(
        side_effect=[
            httpx.Response(429, headers={"retry-after": "0"}),
            httpx.Response(200, json=FIXTURE),
        ]
    )
    async with openfda.OpenFDAClient(base_url=BASE, api_key="k") as client:
        res = await client.search_510k("product_code:QAS")
    assert route.call_count == 2
    assert "api_key=k" in str(route.calls.last.request.url)
    assert len(res.devices) == 2


@pytest.mark.anyio
async def test_search_510k_gives_up_after_retries(respx_mock):
    respx_mock.get(url__startswith=f"{BASE}/device/510k.json").mock(
        return_value=httpx.Response(503)
    )
    async with openfda.OpenFDAClient(base_url=BASE, api_key="", max_retries=1) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.search_510k("product_code:QAS")


@pytest.mark.anyio
async def test_get_510k(respx_mock):
    one = {"meta": FIXTURE["meta"], "results": FIXTURE["results"][:1]}
    respx_mock.get(url__startswith=f"{BASE}/device/510k.json").mock(
        return_value=httpx.Response(200, json=one)
    )
    async with openfda.OpenFDAClient(base_url=BASE, api_key="") as client:
        d = await client.get_510k("k253163")
    assert d is not None and d.k_number == "K253163"
