import httpx
import pytest

from mcp_openfda_predicate import ai_list

CSV_WITH_PREAMBLE = (
    "Artificial Intelligence-Enabled Medical Devices,,,,,\n"
    "Date of Final Decision,Submission Number,Device,Company,Panel (Lead),Primary Product Code\n"
    '06/29/2026,K253628,"Auto-Seg (SO-0012), Spine Auto-Seg (SO-0012)","Agada Medical, Ltd.",Radiology,QIH\n'
    "11/06/2025,K253265,BriefCase-Triage,Aidoc Medical Ltd.,Radiology,QAS\n"
    "02/13/2018,DEN170073,ContaCT,Viz.AI,Radiology,QAS\n"
    "09/29/1995,P950009,AUTOPAP(R) 300 QC AUTOMATIC PAP SCREENER/QC SYSTEM,BD DIAGNOSTICS,Pathology,NMN\n"
    ",,,,,\n"
)


def test_parse_with_preamble_row():
    rows = ai_list.parse_ai_device_csv(CSV_WITH_PREAMBLE)
    assert [r.submission_number for r in rows] == ["K253628", "K253265", "DEN170073", "P950009"]
    k = rows[1]
    assert k.decision_date.isoformat() == "2025-11-06"
    assert k.submission_type == "510k"
    assert k.summary_url == "https://www.accessdata.fda.gov/cdrh_docs/pdf25/K253265.pdf"
    den = rows[2]
    assert den.submission_type == "de_novo"
    assert den.summary_url.endswith("/reviews/DEN170073.pdf")
    assert rows[3].submission_type == "pma" and rows[3].summary_url is None


def test_parse_without_preamble_and_with_bom():
    text = "﻿" + CSV_WITH_PREAMBLE.split("\n", 1)[1]
    rows = ai_list.parse_ai_device_csv(text)
    assert len(rows) == 4


def test_parse_missing_header_raises():
    with pytest.raises(ValueError):
        ai_list.parse_ai_device_csv("a,b,c\n1,2,3\n")


def test_filter_rows():
    rows = ai_list.parse_ai_device_csv(CSV_WITH_PREAMBLE)
    assert [r.submission_number for r in ai_list.filter_rows(rows, product_code="qas")] == [
        "K253265",
        "DEN170073",
    ]
    assert [r.submission_number for r in ai_list.filter_rows(rows, keyword="briefcase aidoc")] == [
        "K253265"
    ]
    assert [r.submission_number for r in ai_list.filter_rows(rows, panel="patho")] == ["P950009"]
    assert [r.submission_number for r in ai_list.filter_rows(rows, year_from=2025)] == [
        "K253628",
        "K253265",
    ]
    assert [r.submission_number for r in ai_list.filter_rows(rows, submission_type="de_novo")] == [
        "DEN170073"
    ]


@pytest.mark.anyio
async def test_cache_downloads_once(respx_mock):
    url = "https://example.test/ai.csv"
    route = respx_mock.get(url).mock(return_value=httpx.Response(200, text=CSV_WITH_PREAMBLE))
    cache = ai_list.AIDeviceListCache(url=url, ttl_seconds=3600)
    a = await cache.rows()
    b = await cache.rows()
    assert len(a) == 4 and a is b
    assert route.call_count == 1
    assert route.calls.last.request.headers["user-agent"].startswith("Mozilla/5.0")
    await cache.rows(force=True)
    assert route.call_count == 2
