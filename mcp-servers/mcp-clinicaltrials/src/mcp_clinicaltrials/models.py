"""Normalised, flat representation of a ClinicalTrials.gov study record."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DesignInfo(BaseModel):
    allocation: str | None = None
    intervention_model: str | None = None
    primary_purpose: str | None = None
    masking: str | None = None
    who_masked: list[str] = Field(default_factory=list)
    observational_model: str | None = None
    time_perspective: str | None = None


class Enrollment(BaseModel):
    count: int | None = None
    type: str | None = Field(default=None, description="ACTUAL or ESTIMATED")


class Intervention(BaseModel):
    type: str | None = None
    name: str | None = None
    description: str | None = None
    arm_group_labels: list[str] = Field(default_factory=list)


class ArmGroup(BaseModel):
    label: str | None = None
    type: str | None = None
    description: str | None = None
    intervention_names: list[str] = Field(default_factory=list)


class Eligibility(BaseModel):
    criteria: str | None = None
    sex: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    std_ages: list[str] = Field(default_factory=list)
    healthy_volunteers: bool | None = None
    study_population: str | None = None
    sampling_method: str | None = None


class Outcome(BaseModel):
    measure: str | None = None
    description: str | None = None
    time_frame: str | None = None


class Reference(BaseModel):
    pmid: str | None = None
    type: str | None = None
    citation: str | None = None


class StudySummary(BaseModel):
    """Compact record returned by search tools."""

    nct_id: str
    brief_title: str | None = None
    official_title: str | None = None
    acronym: str | None = None
    overall_status: str | None = None
    study_type: str | None = None
    phases: list[str] = Field(default_factory=list)
    design_info: DesignInfo = Field(default_factory=DesignInfo)
    enrollment: Enrollment = Field(default_factory=Enrollment)
    conditions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    interventions: list[Intervention] = Field(default_factory=list)
    primary_outcomes: list[Outcome] = Field(default_factory=list)
    start_date: str | None = None
    primary_completion_date: str | None = None
    completion_date: str | None = None
    lead_sponsor: str | None = None
    sponsor_class: str | None = None
    locations_count: int = 0
    countries: list[str] = Field(default_factory=list)
    has_results: bool | None = None
    url: str | None = None


class StudyProtocol(StudySummary):
    """Full normalised protocol (search summary + eligibility, arms, secondary outcomes…)."""

    brief_summary: str | None = None
    detailed_description: str | None = None
    arms: list[ArmGroup] = Field(default_factory=list)
    eligibility: Eligibility = Field(default_factory=Eligibility)
    secondary_outcomes: list[Outcome] = Field(default_factory=list)
    other_outcomes: list[Outcome] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    collaborators: list[str] = Field(default_factory=list)
    is_fda_regulated_device: bool | None = None
    oversight_has_dmc: bool | None = None


# ── parsing ──────────────────────────────────────────────────────────────────


def _g(d: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    cur: Any = d or {}
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _outcomes(items: Any) -> list[Outcome]:
    out: list[Outcome] = []
    for o in items or []:
        if isinstance(o, dict):
            out.append(
                Outcome(
                    measure=o.get("measure"),
                    description=o.get("description"),
                    time_frame=o.get("timeFrame"),
                )
            )
    return out


def parse_study(record: dict[str, Any]) -> StudyProtocol:
    """Convert a raw API v2 study record (``{"protocolSection": …}``) into :class:`StudyProtocol`."""
    ps = record.get("protocolSection") or record
    ident = ps.get("identificationModule") or {}
    status = ps.get("statusModule") or {}
    design = ps.get("designModule") or {}
    dinfo = design.get("designInfo") or {}
    cond = ps.get("conditionsModule") or {}
    arms_mod = ps.get("armsInterventionsModule") or {}
    elig = ps.get("eligibilityModule") or {}
    outcomes = ps.get("outcomesModule") or {}
    sponsor = ps.get("sponsorCollaboratorsModule") or {}
    contacts = ps.get("contactsLocationsModule") or {}
    refs = ps.get("referencesModule") or {}
    desc = ps.get("descriptionModule") or {}
    oversight = ps.get("oversightModule") or {}

    nct_id = ident.get("nctId") or "UNKNOWN"
    locations = contacts.get("locations") or []
    countries = sorted(
        {loc.get("country") for loc in locations if isinstance(loc, dict) and loc.get("country")}
    )

    return StudyProtocol(
        nct_id=nct_id,
        brief_title=ident.get("briefTitle"),
        official_title=ident.get("officialTitle"),
        acronym=ident.get("acronym"),
        overall_status=status.get("overallStatus"),
        study_type=design.get("studyType"),
        phases=list(design.get("phases") or []),
        design_info=DesignInfo(
            allocation=dinfo.get("allocation"),
            intervention_model=dinfo.get("interventionModel"),
            primary_purpose=dinfo.get("primaryPurpose"),
            masking=_g(dinfo, "maskingInfo", "masking"),
            who_masked=list(_g(dinfo, "maskingInfo", "whoMasked", default=[]) or []),
            observational_model=dinfo.get("observationalModel"),
            time_perspective=dinfo.get("timePerspective"),
        ),
        enrollment=Enrollment(
            count=_g(design, "enrollmentInfo", "count"), type=_g(design, "enrollmentInfo", "type")
        ),
        conditions=list(cond.get("conditions") or []),
        keywords=list(cond.get("keywords") or []),
        interventions=[
            Intervention(
                type=i.get("type"),
                name=i.get("name"),
                description=i.get("description"),
                arm_group_labels=list(i.get("armGroupLabels") or []),
            )
            for i in (arms_mod.get("interventions") or [])
            if isinstance(i, dict)
        ],
        arms=[
            ArmGroup(
                label=a.get("label"),
                type=a.get("type"),
                description=a.get("description"),
                intervention_names=list(a.get("interventionNames") or []),
            )
            for a in (arms_mod.get("armGroups") or [])
            if isinstance(a, dict)
        ],
        eligibility=Eligibility(
            criteria=elig.get("eligibilityCriteria"),
            sex=elig.get("sex"),
            minimum_age=elig.get("minimumAge"),
            maximum_age=elig.get("maximumAge"),
            std_ages=list(elig.get("stdAges") or []),
            healthy_volunteers=elig.get("healthyVolunteers"),
            study_population=elig.get("studyPopulation"),
            sampling_method=elig.get("samplingMethod"),
        ),
        primary_outcomes=_outcomes(outcomes.get("primaryOutcomes")),
        secondary_outcomes=_outcomes(outcomes.get("secondaryOutcomes")),
        other_outcomes=_outcomes(outcomes.get("otherOutcomes")),
        start_date=_g(status, "startDateStruct", "date"),
        primary_completion_date=_g(status, "primaryCompletionDateStruct", "date"),
        completion_date=_g(status, "completionDateStruct", "date"),
        lead_sponsor=_g(sponsor, "leadSponsor", "name"),
        sponsor_class=_g(sponsor, "leadSponsor", "class"),
        collaborators=[
            c.get("name")
            for c in (sponsor.get("collaborators") or [])
            if isinstance(c, dict) and c.get("name")
        ],
        locations_count=len(locations),
        countries=countries,
        references=[
            Reference(pmid=r.get("pmid"), type=r.get("type"), citation=r.get("citation"))
            for r in (refs.get("references") or [])
            if isinstance(r, dict)
        ],
        brief_summary=desc.get("briefSummary"),
        detailed_description=desc.get("detailedDescription"),
        is_fda_regulated_device=oversight.get("isFdaRegulatedDevice"),
        oversight_has_dmc=oversight.get("oversightHasDmc"),
        has_results=record.get("hasResults"),
        url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id != "UNKNOWN" else None,
    )


def to_summary(protocol: StudyProtocol) -> StudySummary:
    """Project a full protocol onto the compact search summary."""
    return StudySummary.model_validate(protocol.model_dump(include=set(StudySummary.model_fields)))
