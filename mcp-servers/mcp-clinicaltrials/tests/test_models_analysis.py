from mcp_clinicaltrials import analysis
from mcp_clinicaltrials.models import StudyProtocol, parse_study, to_summary


def test_parse_real_record(study_fixture):
    p = parse_study(study_fixture)
    assert p.nct_id == "NCT06018545"
    assert p.brief_title.startswith("AI Assisted Reader Evaluation")
    assert p.acronym == "AI-REACT"
    assert p.overall_status == "COMPLETED"
    assert p.study_type == "OBSERVATIONAL"
    assert p.design_info.observational_model == "COHORT"
    assert p.design_info.time_perspective == "RETROSPECTIVE"
    assert p.enrollment.count == 33 and p.enrollment.type == "ACTUAL"
    assert "Intracranial Hemorrhages" in p.conditions
    assert "Artificial intelligence" in p.keywords
    assert len(p.arms) == 2 and p.arms[0].label == "Readers"
    assert any(i.name == "Ground truthing" for i in p.interventions)
    assert len(p.primary_outcomes) >= 8
    assert p.primary_outcomes[0].measure.startswith("Reader performance: Sensitivity")
    assert p.eligibility.sex == "ALL" and p.eligibility.healthy_volunteers is True
    assert p.lead_sponsor == "Oxford University Hospitals NHS Trust"
    assert p.locations_count == 4 and p.countries == ["United Kingdom"]
    assert p.references and p.references[0].pmid == "31206250"
    assert p.start_date == "2023-06-01"
    assert p.url == "https://clinicaltrials.gov/study/NCT06018545"


def test_parse_is_defensive_on_sparse_record():
    p = parse_study({"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}})
    assert p.nct_id == "NCT00000001"
    assert p.enrollment.count is None
    assert p.arms == [] and p.primary_outcomes == []
    assert p.locations_count == 0
    # entirely empty record does not raise either
    assert parse_study({}).nct_id == "UNKNOWN"


def test_to_summary_projects_fields(study_fixture):
    s = to_summary(parse_study(study_fixture))
    assert s.nct_id == "NCT06018545"
    assert not hasattr(s, "eligibility")
    assert s.enrollment.count == 33


def test_extract_eligibility_bullets(study_fixture):
    crit = parse_study(study_fixture).eligibility.criteria
    b = analysis.extract_eligibility_bullets(crit)
    assert b.inclusion == [
        "Radiologists/Radiographers/ED clinicians who review CT head scans as part of their clinical practice"
    ]
    assert len(b.exclusion) == 3 and b.exclusion[0] == "Neuroradiologists."
    assert b.unclassified == []


def test_extract_eligibility_bullets_handles_numbered_and_empty():
    b = analysis.extract_eligibility_bullets(
        "Inclusion Criteria:\n1. Age ≥ 20 years\n2) Head CT\nExclusion Criteria:\n- Metal artefact\n"
    )
    assert b.inclusion == ["Age ≥ 20 years", "Head CT"]
    assert b.exclusion == ["Metal artefact"]
    assert analysis.extract_eligibility_bullets(None) == analysis.EligibilityBullets()
    assert analysis.extract_eligibility_bullets("Adults only").unclassified == ["Adults only"]


def _mk(nct: str, **kw) -> StudyProtocol:
    base = {"protocolSection": {"identificationModule": {"nctId": nct}}}
    p = parse_study(base)
    return p.model_copy(update=kw)


def test_summarize_design_patterns(study_fixture, search_fixture):
    studies = [parse_study(study_fixture)] + [parse_study(s) for s in search_fixture["studies"]]
    summary = analysis.summarize_design_patterns(studies)
    assert summary.n_studies == 3
    assert summary.study_types["OBSERVATIONAL"] == 2 and summary.study_types["INTERVENTIONAL"] == 1
    assert summary.time_perspectives["RETROSPECTIVE"] == 2
    assert summary.allocations.get("RANDOMIZED") == 1
    assert summary.enrollment.n_studies_with_count == 3
    assert summary.enrollment.minimum == 33
    assert summary.endpoint_keyword_frequency["sensitivity"] >= 1
    assert summary.endpoint_keyword_frequency["auc_auroc"] >= 1
    assert summary.endpoint_keyword_frequency["reading_time"] >= 1
    assert "United Kingdom" in summary.countries
    assert summary.notes == []


def test_summarize_handles_empty_and_missing_counts():
    empty = analysis.summarize_design_patterns([])
    assert (
        empty.n_studies == 0 and empty.enrollment.median is None and "No studies" in empty.notes[0]
    )
    from mcp_clinicaltrials.models import Eligibility, Enrollment

    s1 = _mk(
        "NCT1",
        enrollment=Enrollment(count=100, type="ESTIMATED"),
        eligibility=Eligibility(criteria="Adults aged 18 years or older", minimum_age="18 Years"),
    )
    s2 = _mk("NCT2")
    summary = analysis.summarize_design_patterns([s1, s2])
    assert summary.enrollment.median == 100 and summary.enrollment.q1 == 100
    assert any("lack an enrollment count" in n for n in summary.notes)
    assert any("NCT1" in snip for snip in summary.age_limit_snippets)
