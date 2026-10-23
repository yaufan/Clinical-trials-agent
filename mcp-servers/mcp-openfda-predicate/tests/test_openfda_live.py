"""Live checks against FDA endpoints. Enable with LIVE_API_TESTS=1."""

import os

import pytest
from mcp.client.client import Client

from mcp_openfda_predicate import openfda, pdfs
from mcp_openfda_predicate.server import server

live = pytest.mark.skipif(
    os.environ.get("LIVE_API_TESTS") != "1", reason="set LIVE_API_TESTS=1 to hit real FDA endpoints"
)


@live
@pytest.mark.live
@pytest.mark.anyio
async def test_live_openfda_qas_search():
    async with openfda.OpenFDAClient() as client:
        res = await client.search_510k(
            openfda.build_510k_query(product_code="QAS", decision_date_from="2023-01-01"), limit=5
        )
    assert res.meta.total > 10
    assert all(d.product_code == "QAS" for d in res.devices)


@live
@pytest.mark.live
@pytest.mark.anyio
async def test_live_openfda_keyword_no_match_is_empty():
    async with openfda.OpenFDAClient() as client:
        res = await client.search_510k("product_code:ZZZZ9")
    assert res.devices == []


@live
@pytest.mark.live
@pytest.mark.anyio
async def test_live_510k_summary_extraction():
    # K183285 (CureMetrix cmTriage, QAS) has a public 510(k) summary with a Performance Data section.
    res = await pdfs.fetch_pdf_text(pdfs.k_number_to_summary_url("K183285"))
    assert res.found and res.pages >= 5
    ex = pdfs.extract_clinical_summary(res.text, own_k_number="K183285")
    assert any(m.metric in ("sensitivity", "specificity") for m in ex.metrics)
    assert ex.n_cases and ex.n_cases >= 100
    assert "retrospective" in ex.design_keywords


@live
@pytest.mark.live
@pytest.mark.anyio
async def test_live_denovo_and_ai_list_via_server():
    async with Client(server) as client:
        den = await client.call_tool("extract_denovo_clinical_summary", {"den_number": "DEN170073"})
        assert den.structured_content["pdf_found"] is True
        assert den.structured_content["extract"]["n_cases"] >= 100
        lst = await client.call_tool(
            "search_fda_ai_device_list", {"product_code": "QAS", "year_from": 2024, "limit": 5}
        )
        assert lst.structured_content["total_in_list"] > 1000
        assert lst.structured_content["matched"] >= 5
