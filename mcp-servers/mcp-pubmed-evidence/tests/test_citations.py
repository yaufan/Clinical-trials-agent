from mcp_pubmed_evidence.citations import format_apa, format_citation, format_vancouver
from mcp_pubmed_evidence.models import PubMedArticle

ART = PubMedArticle(
    pmid="31000001",
    title="Diagnostic Performance of Radiologists for Acute Intracranial Hemorrhage on Noncontrast Head CT",
    journal="Radiology",
    journal_abbreviation="Radiology",
    year=2021,
    volume="298",
    issue="2",
    pages="345-53",
    authors=["Smith JA", "Lee K", "Chen W", "Garcia M", "Okafor T", "Patel R", "Nguyen L"],
    doi="10.1148/radiol.2021000001",
)


def test_vancouver_truncates_to_six_authors_with_et_al():
    ref = format_vancouver(ART)
    assert ref.startswith(
        "Smith JA, Lee K, Chen W, Garcia M, Okafor T, Patel R, et al. Diagnostic Performance"
    )
    assert "Radiology. 2021;298(2):345-53." in ref
    assert "doi:10.1148/radiol.2021000001." in ref
    assert ref.endswith("PMID: 31000001.")
    assert "Nguyen" not in ref


def test_vancouver_handles_sparse_record():
    sparse = PubMedArticle(pmid="1", title="A title", journal="J Test", year=2020)
    assert format_vancouver(sparse) == "A title. J Test. 2020. PMID: 1."


def test_apa_formatting():
    ref = format_apa(ART)
    assert ref.startswith(
        "Smith, J. A., Lee, K., Chen, W., Garcia, M., Okafor, T., Patel, R., & Nguyen, L. (2021)."
    )
    assert "Radiology, 298(2), 345–53." in ref
    assert ref.endswith("https://doi.org/10.1148/radiol.2021000001")


def test_format_citation_dispatch():
    assert format_citation(ART, "apa") == format_apa(ART)
    assert format_citation(ART) == format_vancouver(ART)
