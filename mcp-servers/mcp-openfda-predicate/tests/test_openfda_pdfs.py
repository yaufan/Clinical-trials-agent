import pytest
from _openfda_pdf_fixture import SUMMARY_SENTENCES, build_pdf

from mcp_openfda_predicate import pdfs


@pytest.mark.parametrize(
    "k,expected",
    [
        ("K210123", "https://www.accessdata.fda.gov/cdrh_docs/pdf21/K210123.pdf"),
        ("K083540", "https://www.accessdata.fda.gov/cdrh_docs/pdf8/K083540.pdf"),
        ("K101234", "https://www.accessdata.fda.gov/cdrh_docs/pdf10/K101234.pdf"),
        ("K001234", "https://www.accessdata.fda.gov/cdrh_docs/pdf/K001234.pdf"),
        ("K991234", "https://www.accessdata.fda.gov/cdrh_docs/pdf/K991234.pdf"),
        ("k183285", "https://www.accessdata.fda.gov/cdrh_docs/pdf18/K183285.pdf"),
    ],
)
def test_k_number_url_rule(k, expected):
    assert pdfs.k_number_to_summary_url(k) == expected


def test_k_number_validation():
    with pytest.raises(ValueError):
        pdfs.k_number_to_summary_url("K12345")
    with pytest.raises(ValueError):
        pdfs.k_number_to_summary_url("DEN170073")


def test_den_url_rule():
    assert (
        pdfs.den_number_to_summary_url("den170073")
        == "https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN170073.pdf"
    )
    with pytest.raises(ValueError):
        pdfs.den_number_to_summary_url("K170073")


def test_pdf_fixture_roundtrips_text():
    text, pages, truncated = pdfs.pdf_bytes_to_text(build_pdf())
    assert pages == 1 and not truncated
    assert "sensitivity of 93.5%" in text
    assert "12 radiologists" in text


def test_extract_clinical_summary_from_fixture():
    text = "\n".join(SUMMARY_SENTENCES)
    ex = pdfs.extract_clinical_summary(
        text, source_url="http://x/K000001.pdf", pages=1, own_k_number="K000001"
    )
    metrics = {m.metric: m for m in ex.metrics}
    assert metrics["sensitivity"].value == pytest.approx(0.935)
    assert metrics["sensitivity"].ci_lower == pytest.approx(0.912)
    assert metrics["sensitivity"].ci_upper == pytest.approx(0.951)
    assert metrics["specificity"].value == pytest.approx(0.89)
    assert metrics["auc"].value == pytest.approx(0.95)
    assert ex.n_cases == 500
    assert ex.n_readers == 12
    assert ex.n_sites == 4
    assert any("consensus" in s.lower() for s in ex.ground_truth_sentences)
    for kw in (
        "retrospective",
        "multicenter",
        "standalone",
        "multi-reader",
        "fully-crossed",
        "washout",
        "blinded",
        "consecutive",
        "performance-goal",
    ):
        assert kw in ex.design_keywords
    assert ex.predicate_k_numbers == ["K183285"]
    assert any("performance goal" in s.lower() for s in ex.performance_goal_sentences)
    assert ex.section_excerpts and ex.section_excerpts[0].startswith("7. Performance Data")
    assert ex.confidence == "high"


def test_extract_handles_fraction_metrics_and_messy_whitespace():
    text = (
        "7.  Performance  Data\n"
        "The  study  evaluated  300  consecutively  collected  contrast-enhanced  abdominal  CT  cases.\n"
        "The  appendicitis  status  of  each  case  was  independently  assessed  by  three  U.S.  board-certified  radiologists,  with  the  reference  standard  (ground  truth)  determined  by  majority  agreement,  yielding  139  positive  and  161  negative  cases.\n"
        "EFAI demonstrated sensitivity of 0.932 (95% CI: 0.882–0.961) and specificity of 0.901 (95% CI: 0.850–0.938)."
    )
    ex = pdfs.extract_clinical_summary(text)
    m = {x.metric: x for x in ex.metrics}
    assert m["sensitivity"].value == pytest.approx(0.932)
    assert m["sensitivity"].ci_lower == pytest.approx(0.882)
    assert m["specificity"].value == pytest.approx(0.901)
    assert ex.n_cases == 300
    assert ex.n_readers == 3  # "three U.S. board-certified radiologists"
    assert any(c.kind == "positives" and c.value == 139 for c in ex.counts)
    assert any(c.kind == "negatives" and c.value == 161 for c in ex.counts)


def test_extract_low_confidence_on_unrelated_text():
    ex = pdfs.extract_clinical_summary(
        "Indications for use: the device is intended for adults. Sterility: not applicable."
    )
    assert ex.confidence == "low"
    assert ex.metrics == [] and ex.n_cases is None
    assert any("No clinical/performance heading" in n for n in ex.notes)


def test_aggregate_benchmarks():
    a = pdfs.extract_clinical_summary("\n".join(SUMMARY_SENTENCES))
    b = pdfs.extract_clinical_summary(
        "Performance Data\nA retrospective study of 300 cases with 6 readers showed sensitivity of 90% and specificity of 85%."
    )
    missing = pdfs.ClinicalSummaryExtract(pdf_found=False)
    agg = pdfs.aggregate_benchmarks([a, b, missing])
    assert agg.devices_requested == 3 and agg.devices_with_summary == 2
    assert agg.median_cases == 400
    assert agg.cases_range == (300, 500)
    assert agg.readers_range == (6, 12)
    assert agg.sensitivity_range == (0.9, 0.935)
    assert agg.specificity_range == (0.85, 0.89)
    assert agg.design_keyword_frequency["retrospective"] == 2


@pytest.mark.anyio
async def test_fetch_pdf_text_404_and_success(respx_mock):
    import httpx

    url = "https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180001.pdf"
    route = respx_mock.get(url).mock(return_value=httpx.Response(404, text="not found"))
    res = await pdfs.fetch_pdf_text(url)
    assert res.found is False and res.status_code == 404
    assert route.calls.last.request.headers["user-agent"].startswith("Mozilla/5.0")

    respx_mock.get(url).mock(
        return_value=httpx.Response(
            200, content=build_pdf(), headers={"content-type": "application/pdf"}
        )
    )
    res = await pdfs.fetch_pdf_text(url)
    assert res.found and res.pages == 1 and "93.5%" in res.text


@pytest.mark.anyio
async def test_fetch_pdf_text_rejects_html(respx_mock):
    import httpx

    url = "https://www.accessdata.fda.gov/cdrh_docs/pdf18/K180002.pdf"
    respx_mock.get(url).mock(return_value=httpx.Response(200, text="<html>login</html>"))
    res = await pdfs.fetch_pdf_text(url)
    assert res.found is False and "not a PDF" in (res.error or "")
