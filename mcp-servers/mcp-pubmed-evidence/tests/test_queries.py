from datetime import date

import pytest

from mcp_pubmed_evidence.queries import AI_TERMS, build_ai_evidence_query, build_baseline_query

TODAY = date(2026, 10, 23)


def test_baseline_query_has_field_tags_and_ai_exclusion():
    q = build_baseline_query(
        "intracranial hemorrhage", "computed tomography", "sensitivity", years=10, today=TODAY
    )
    assert q.purpose == "baseline_unaided"
    assert '"intracranial hemorrhage"[tiab]' in q.query
    assert '"intracranial hemorrhage"[MeSH Terms]' in q.query
    assert '"computed tomography"[tiab]' in q.query
    assert '"Sensitivity and Specificity"[MeSH Terms]' in q.query
    assert '"Humans"[MeSH Terms]' in q.query
    assert '("2016/01/01"[dp] : "2026/12/31"[dp])' in q.query
    assert q.query.count(" NOT ") == 1
    tail = q.query.split(" NOT ", 1)[1]
    for term in AI_TERMS:
        assert term in tail
    assert '"radiologist*"[tiab]' in q.query


def test_baseline_query_can_keep_ai_papers():
    q = build_baseline_query("diabetic retinopathy", exclude_ai=False, years=None, today=TODAY)
    assert "NOT" not in q.query
    assert "date" not in q.components
    assert "modality" not in q.components


def test_unknown_metric_falls_back_to_topic_clause():
    q = build_baseline_query("lung nodule", metric="FROC", today=TODAY)
    assert '"FROC"[tiab]' in q.components["metric"]


def test_ai_evidence_query_requires_ai_terms():
    q = build_ai_evidence_query("lung nodule", "chest CT", "auc", years=5, today=TODAY)
    assert q.purpose == "ai_evidence"
    assert "NOT" not in q.query
    assert '"deep learning"[tiab]' in q.components["ai"]
    assert '"ROC Curve"[MeSH Terms]' in q.query
    assert '"2021/01/01"[dp]' in q.query


def test_disease_required():
    with pytest.raises(ValueError):
        build_baseline_query("  ")
