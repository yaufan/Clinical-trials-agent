"""Deterministic PubMed query builders.

The point of a *baseline* query is to find how unaided clinicians perform on the target task
(sensitivity / specificity / AUC) so the biostatistician can anchor the performance goal and
the protocol's background section. The *AI evidence* query is the inverse: prior AI studies
on the same task, useful for the predicate / literature review.
"""

from __future__ import annotations

from datetime import date

from .models import QueryResponse

AI_TERMS = [
    '"deep learning"[tiab]',
    '"artificial intelligence"[tiab]',
    '"machine learning"[tiab]',
    '"convolutional"[tiab]',
    '"neural network"[tiab]',
    '"computer-aided"[tiab]',
    '"computer aided"[tiab]',
]

METRIC_TERMS: dict[str, list[str]] = {
    "sensitivity": ['"sensitivity"[tiab]', '"Sensitivity and Specificity"[MeSH Terms]'],
    "specificity": ['"specificity"[tiab]', '"Sensitivity and Specificity"[MeSH Terms]'],
    "auroc": ['"area under the curve"[tiab]', '"AUC"[tiab]', '"ROC Curve"[MeSH Terms]'],
    "auc": ['"area under the curve"[tiab]', '"AUC"[tiab]', '"ROC Curve"[MeSH Terms]'],
    "accuracy": ['"diagnostic accuracy"[tiab]', '"accuracy"[tiab]'],
    "ppv": ['"positive predictive value"[tiab]', '"Predictive Value of Tests"[MeSH Terms]'],
    "npv": ['"negative predictive value"[tiab]', '"Predictive Value of Tests"[MeSH Terms]'],
    "dice": ['"Dice"[tiab]', '"segmentation"[tiab]'],
    "reader_time": ['"reading time"[tiab]', '"interpretation time"[tiab]'],
}

DIAGNOSTIC_PERFORMANCE_TERMS = [
    '"sensitivity"[tiab]',
    '"specificity"[tiab]',
    '"diagnostic accuracy"[tiab]',
    '"area under the curve"[tiab]',
    '"Sensitivity and Specificity"[MeSH Terms]',
]

READER_TERMS = [
    '"radiologist*"[tiab]',
    '"reader*"[tiab]',
    '"physician*"[tiab]',
    '"clinician*"[tiab]',
    '"observer*"[tiab]',
    '"interpretation"[tiab]',
]


def _quote(term: str) -> str:
    term = term.strip()
    return term if term.startswith('"') else f'"{term}"'


def _or(clauses: list[str]) -> str:
    uniq = list(dict.fromkeys(c for c in clauses if c))
    return "(" + " OR ".join(uniq) + ")" if len(uniq) > 1 else (uniq[0] if uniq else "")


def _topic_clause(text: str) -> str:
    """Match a free-text topic in title/abstract and as a MeSH term."""
    q = _quote(text)
    return _or([f"{q}[tiab]", f"{q}[MeSH Terms]"])


def _date_clause(years: int | None, *, today: date | None = None) -> str:
    if not years or years <= 0:
        return ""
    today = today or date.today()
    start = today.year - years
    return f'("{start}/01/01"[dp] : "{today.year}/12/31"[dp])'


def _metric_clause(metric: str | None) -> str:
    if not metric:
        return _or(DIAGNOSTIC_PERFORMANCE_TERMS)
    key = metric.strip().lower().replace("-", "_").replace(" ", "_")
    terms = METRIC_TERMS.get(key)
    if terms is None:
        return _topic_clause(metric)
    return _or(terms)


def build_baseline_query(
    disease: str,
    modality: str | None = None,
    metric: str | None = None,
    *,
    exclude_ai: bool = True,
    years: int | None = None,
    humans_only: bool = True,
    today: date | None = None,
) -> QueryResponse:
    """Query for *unaided clinician* baseline diagnostic performance on ``disease``."""
    if not disease or not disease.strip():
        raise ValueError("disease is required")
    components: dict[str, str] = {"disease": _topic_clause(disease)}
    if modality and modality.strip():
        components["modality"] = _topic_clause(modality)
    components["metric"] = _metric_clause(metric)
    components["readers"] = _or(READER_TERMS)
    if humans_only:
        components["humans"] = '"Humans"[MeSH Terms]'
    date_clause = _date_clause(years, today=today)
    if date_clause:
        components["date"] = date_clause
    query = " AND ".join(components.values())
    if exclude_ai:
        components["exclude_ai"] = "NOT " + _or(AI_TERMS)
        query = f"{query} NOT {_or(AI_TERMS)}"
    return QueryResponse(query=query, components=components, purpose="baseline_unaided")


def build_ai_evidence_query(
    disease: str,
    modality: str | None = None,
    metric: str | None = None,
    *,
    years: int | None = None,
    humans_only: bool = True,
    today: date | None = None,
) -> QueryResponse:
    """Query for prior AI/ML studies on the same clinical task."""
    if not disease or not disease.strip():
        raise ValueError("disease is required")
    components: dict[str, str] = {"disease": _topic_clause(disease)}
    if modality and modality.strip():
        components["modality"] = _topic_clause(modality)
    components["ai"] = _or(AI_TERMS)
    components["metric"] = _metric_clause(metric)
    if humans_only:
        components["humans"] = '"Humans"[MeSH Terms]'
    date_clause = _date_clause(years, today=today)
    if date_clause:
        components["date"] = date_clause
    return QueryResponse(
        query=" AND ".join(components.values()), components=components, purpose="ai_evidence"
    )
