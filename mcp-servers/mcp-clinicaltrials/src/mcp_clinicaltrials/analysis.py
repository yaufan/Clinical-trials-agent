"""Deterministic design-pattern statistics over normalised studies (no LLM involved)."""

from __future__ import annotations

import re
import statistics
from collections import Counter

from pydantic import BaseModel, Field

from .models import StudyProtocol

# Endpoint keyword families frequently seen in AI-SaMD validation studies.
ENDPOINT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sensitivity": ("sensitivity", "true positive rate", "recall"),
    "specificity": ("specificity", "true negative rate"),
    "auc_auroc": ("auc", "auroc", "area under", "roc"),
    "ppv_npv": ("ppv", "npv", "positive predictive", "negative predictive", "precision"),
    "reading_time": (
        "reading time",
        "read time",
        "interpretation time",
        "time to",
        "turnaround",
        "review time",
        "time taken",
        "reader speed",
        "mean time",
        "reporting time",
    ),
    "detection_rate": ("detection rate", "adenoma detection", "miss rate", "cancer detection"),
    "froc_afroc": ("froc", "afroc", "lesion localization", "localisation"),
    "dice_segmentation": ("dice", "jaccard", "iou", "segmentation accuracy", "hausdorff"),
    "accuracy": ("accuracy", "concordance", "agreement", "kappa"),
    "reader_confidence": ("confidence",),
    "clinical_outcome": (
        "mortality",
        "length of stay",
        "door-to",
        "time to treatment",
        "readmission",
    ),
}

AGE_PATTERN = re.compile(
    r"(?:(?:aged?|age)\s*(?:of\s*)?(?:≥|>=|>|at least|over|older than)?\s*\d{1,3}\s*(?:years?|yrs?|y/?o)?"
    r"|\d{1,3}\s*(?:years?|yrs?)\s*(?:of age|or older|and older|and above|or above))",
    re.IGNORECASE,
)


class EligibilityBullets(BaseModel):
    inclusion: list[str] = Field(default_factory=list)
    exclusion: list[str] = Field(default_factory=list)
    unclassified: list[str] = Field(default_factory=list)


def extract_eligibility_bullets(criteria_text: str | None) -> EligibilityBullets:
    """Split a free-text eligibility block into inclusion / exclusion bullet lists.

    ClinicalTrials.gov criteria usually look like ``Inclusion Criteria:\\n\\n* item\\n* item\\n\\n
    Exclusion Criteria:\\n\\n* item``. Bullets may use ``*``, ``-``, ``•`` or ``1.`` prefixes.
    """
    result = EligibilityBullets()
    if not criteria_text:
        return result
    section: str | None = None
    for raw in criteria_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower().rstrip(":").strip()
        if low.startswith("inclusion"):
            section = "inclusion"
            continue
        if low.startswith("exclusion"):
            section = "exclusion"
            continue
        item = re.sub(r"^(?:[*\-•·]|\d+[.)])\s*", "", line).strip()
        if not item:
            continue
        if section == "inclusion":
            result.inclusion.append(item)
        elif section == "exclusion":
            result.exclusion.append(item)
        else:
            result.unclassified.append(item)
    return result


class EnrollmentStats(BaseModel):
    n_studies_with_count: int = 0
    median: float | None = None
    q1: float | None = None
    q3: float | None = None
    minimum: int | None = None
    maximum: int | None = None
    actual_vs_estimated: dict[str, int] = Field(default_factory=dict)


class DesignPatternSummary(BaseModel):
    n_studies: int
    nct_ids: list[str]
    study_types: dict[str, int] = Field(default_factory=dict)
    time_perspectives: dict[str, int] = Field(default_factory=dict)
    observational_models: dict[str, int] = Field(default_factory=dict)
    allocations: dict[str, int] = Field(default_factory=dict)
    intervention_models: dict[str, int] = Field(default_factory=dict)
    masking: dict[str, int] = Field(default_factory=dict)
    statuses: dict[str, int] = Field(default_factory=dict)
    enrollment: EnrollmentStats = Field(default_factory=EnrollmentStats)
    endpoint_keyword_frequency: dict[str, int] = Field(
        default_factory=dict,
        description="Number of studies whose primary outcomes mention each endpoint family",
    )
    primary_outcome_measures: list[str] = Field(default_factory=list)
    age_limit_snippets: list[str] = Field(default_factory=list)
    countries: dict[str, int] = Field(default_factory=dict)
    conditions: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


def _count(values: list[str | None]) -> dict[str, int]:
    return dict(Counter(v for v in values if v))


def _quartiles(values: list[int]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    if len(values) == 1:
        v = float(values[0])
        return v, v, v
    q = statistics.quantiles(values, n=4, method="inclusive")
    return q[0], float(statistics.median(values)), q[2]


def summarize_design_patterns(studies: list[StudyProtocol]) -> DesignPatternSummary:
    """Aggregate design characteristics across studies for the Predicate Benchmark Matrix."""
    counts = [s.enrollment.count for s in studies if s.enrollment.count is not None]
    q1, med, q3 = _quartiles(counts)
    kw_freq: Counter[str] = Counter()
    measures: list[str] = []
    for s in studies:
        text = " ".join(
            filter(
                None,
                [o.measure for o in s.primary_outcomes]
                + [o.description for o in s.primary_outcomes],
            )
        ).lower()
        for fam, needles in ENDPOINT_KEYWORDS.items():
            if any(n in text for n in needles):
                kw_freq[fam] += 1
        measures.extend(o.measure for o in s.primary_outcomes if o.measure)
    age_snips: list[str] = []
    for s in studies:
        crit = s.eligibility.criteria or ""
        for m in AGE_PATTERN.finditer(crit):
            start = max(0, m.start() - 40)
            snippet = crit[start : m.end() + 40].replace("\n", " ").strip()
            age_snips.append(f"{s.nct_id}: …{snippet}…")
        if s.eligibility.minimum_age or s.eligibility.maximum_age:
            age_snips.append(
                f"{s.nct_id}: minimum_age={s.eligibility.minimum_age or 'n/a'}, maximum_age={s.eligibility.maximum_age or 'n/a'}"
            )
    countries: Counter[str] = Counter()
    conditions: Counter[str] = Counter()
    for s in studies:
        countries.update(s.countries)
        conditions.update(c.strip() for c in s.conditions)
    notes = []
    if not studies:
        notes.append("No studies supplied.")
    if counts and len(counts) < len(studies):
        notes.append(f"{len(studies) - len(counts)} study(ies) lack an enrollment count.")
    return DesignPatternSummary(
        n_studies=len(studies),
        nct_ids=[s.nct_id for s in studies],
        study_types=_count([s.study_type for s in studies]),
        time_perspectives=_count([s.design_info.time_perspective for s in studies]),
        observational_models=_count([s.design_info.observational_model for s in studies]),
        allocations=_count([s.design_info.allocation for s in studies]),
        intervention_models=_count([s.design_info.intervention_model for s in studies]),
        masking=_count([s.design_info.masking for s in studies]),
        statuses=_count([s.overall_status for s in studies]),
        enrollment=EnrollmentStats(
            n_studies_with_count=len(counts),
            median=med,
            q1=q1,
            q3=q3,
            minimum=min(counts) if counts else None,
            maximum=max(counts) if counts else None,
            actual_vs_estimated=_count(
                [s.enrollment.type for s in studies if s.enrollment.count is not None]
            ),
        ),
        endpoint_keyword_frequency=dict(kw_freq),
        primary_outcome_measures=measures,
        age_limit_snippets=age_snips[:50],
        countries=dict(countries.most_common(20)),
        conditions=dict(conditions.most_common(20)),
        notes=notes,
    )
