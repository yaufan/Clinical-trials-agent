"""In-process MCP round-trip through the official client (no sockets)."""

import json
from pathlib import Path

import httpx
import pytest
from _openfda_pdf_fixture import build_pdf
from mcp.client.client import Client

from mcp_openfda_predicate import server as srv
from mcp_openfda_predicate.server import server

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openfda_510k_qas.json").read_text())


@pytest.mark.anyio
async def test_tools_listed():
    async with Client(server) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert names == {
            "find_predicate_devices",
            "get_510k_record",
            "extract_510k_clinical_summary",
            "extract_denovo_clinical_summary",
            "search_fda_ai_device_list",
            "summarize_predicate_benchmarks",
        }
        fp = next(t for t in tools.tools if t.name == "find_predicate_devices")
        assert "product_code" in fp.input_schema["properties"]
        assert fp.output_schema is not None


@pytest.mark.anyio
async def test_find_predicate_devices_roundtrip(respx_mock):
    respx_mock.get(url__startswith="https://api.fda.gov/device/510k.json").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "find_predicate_devices", {"product_code": "QAS", "limit": 2}
        )
    assert not result.is_error
    sc = result.structured_content
    assert sc["meta"]["total"] == 89
    assert sc["devices"][0]["k_number"] == "K253163"


@pytest.mark.anyio
async def test_find_predicate_devices_requires_criteria():
    async with Client(server) as client:
        result = await client.call_tool("find_predicate_devices", {})
    assert result.is_error


@pytest.mark.anyio
async def test_extract_510k_summary_found_and_missing(respx_mock):
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180001.pdf").mock(
        return_value=httpx.Response(
            200, content=build_pdf(), headers={"content-type": "application/pdf"}
        )
    )
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/pdf21/K210123.pdf").mock(
        return_value=httpx.Response(404)
    )
    async with Client(server) as client:
        ok = await client.call_tool("extract_510k_clinical_summary", {"k_number": "K180001"})
        missing = await client.call_tool("extract_510k_clinical_summary", {"k_number": "K210123"})
    assert not ok.is_error
    sc = ok.structured_content
    assert sc["pdf_found"] is True
    assert sc["extract"]["n_cases"] == 500 and sc["extract"]["n_readers"] == 12
    assert {m["metric"] for m in sc["extract"]["metrics"]} >= {"sensitivity", "specificity", "auc"}
    msc = missing.structured_content
    assert msc["pdf_found"] is False and msc["http_status"] == 404
    assert msc["summary_url"].endswith("/pdf21/K210123.pdf")


@pytest.mark.anyio
async def test_extract_denovo_summary(respx_mock):
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN170073.pdf").mock(
        return_value=httpx.Response(
            200, content=build_pdf(), headers={"content-type": "application/pdf"}
        )
    )
    async with Client(server) as client:
        res = await client.call_tool("extract_denovo_clinical_summary", {"den_number": "DEN170073"})
    assert res.structured_content["pdf_found"] is True
    assert res.structured_content["extract"]["n_cases"] == 500


@pytest.mark.anyio
async def test_search_fda_ai_device_list(respx_mock, monkeypatch):
    csv_text = (
        "Date of Final Decision,Submission Number,Device,Company,Panel (Lead),Primary Product Code\n"
        "11/06/2025,K253265,BriefCase-Triage,Aidoc Medical Ltd.,Radiology,QAS\n"
        "02/13/2018,DEN170073,ContaCT,Viz.AI,Radiology,QAS\n"
        "06/29/2026,K253628,Auto-Seg,Agada Medical,Radiology,QIH\n"
    )
    url = "https://example.test/ai.csv"
    respx_mock.get(url).mock(return_value=httpx.Response(200, text=csv_text))
    monkeypatch.setattr(srv, "_ai_cache", srv.ai_list.AIDeviceListCache(url=url))
    async with Client(server) as client:
        res = await client.call_tool(
            "search_fda_ai_device_list", {"product_code": "QAS", "limit": 10}
        )
    sc = res.structured_content
    assert sc["total_in_list"] == 3 and sc["matched"] == 2
    assert [d["submission_number"] for d in sc["devices"]] == ["K253265", "DEN170073"]


@pytest.mark.anyio
async def test_summarize_predicate_benchmarks(respx_mock):
    pdf = build_pdf()
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180001.pdf").mock(
        return_value=httpx.Response(200, content=pdf)
    )
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/pdf19/K190002.pdf").mock(
        return_value=httpx.Response(404)
    )
    respx_mock.get("https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN170073.pdf").mock(
        return_value=httpx.Response(200, content=pdf)
    )
    async with Client(server) as client:
        res = await client.call_tool(
            "summarize_predicate_benchmarks",
            {"submission_numbers": ["K180001", "K190002", "DEN170073", "bogus"]},
        )
    assert not res.is_error
    sc = res.structured_content
    assert len(sc["devices"]) == 4
    agg = sc["aggregate"]
    assert agg["devices_requested"] == 4 and agg["devices_with_summary"] == 2
    assert agg["median_cases"] == 500 and agg["readers_range"] == [12, 12]
    bogus = next(d for d in sc["devices"] if d["submission_number"] == "BOGUS")
    assert bogus["pdf_found"] is False and "not a 510(k) number" in bogus["error"]
