"""Run state: everything the pipeline produces, persisted as JSON and streamed to the UI."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class RunStage(StrEnum):
    created = "created"
    triage = "triage"
    harvest = "harvest"
    awaiting_evidence_confirmation = "awaiting_evidence_confirmation"
    biostat = "biostat"
    write = "write"
    audit = "audit"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunEvent(BaseModel):
    ts: datetime = Field(default_factory=utcnow)
    type: str = Field(
        description="stage_started | stage_completed | progress | tool_call | hitl_required | error | log"
    )
    stage: RunStage | None = None
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


# ── Stage 1: regulatory triage ───────────────────────────────────────────────
class TriageDecision(BaseModel):
    study_archetype: str = Field(
        description="standalone_diagnostic_accuracy | mrmc_reader_study | hybrid | prospective_interventional"
    )
    regulatory_pathways: list[str]
    applicable_checklists: list[dict[str, str]] = Field(
        description="[{checklist_id, role, rationale}] from mcp-regulatory-rag"
    )
    significant_risk_assessment: str = Field(
        description="e.g. likely non-significant-risk retrospective study under 醫療器材管理法 §37 — for IRB planning"
    )
    key_regulatory_considerations: list[str]
    recommended_statistical_framework: str
    rationale: str


# ── Stage 2: evidence harvest ────────────────────────────────────────────────
class EvidenceItem(BaseModel):
    source: str = Field(description="clinicaltrials | openfda | pubmed | regulatory_rag")
    ref_id: str = Field(description="NCT id, K number, PMID or document id")
    title: str
    url: str | None = None
    summary: str = ""
    design: str | None = None
    sample_size: str | None = None
    readers: str | None = None
    endpoints: list[str] = Field(default_factory=list)
    reported_performance: dict[str, Any] = Field(default_factory=dict)
    ground_truth: str | None = None
    eligibility_highlights: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    accepted: bool = True
    user_note: str | None = None


class BenchmarkRow(BaseModel):
    parameter: str
    predicate_or_literature_values: list[str]
    proposed_value: str
    justification: str


class EvidenceMatrix(BaseModel):
    items: list[EvidenceItem]
    benchmark_rows: list[BenchmarkRow] = Field(default_factory=list)
    narrative_summary: str = ""
    baseline_performance: dict[str, Any] = Field(
        default_factory=dict, description="e.g. unaided reader sensitivity/specificity from PubMed"
    )
    gaps_and_warnings: list[str] = Field(default_factory=list)
    confirmed: bool = False
    confirmed_at: datetime | None = None
    reviewer_notes: str | None = None


# ── Stage 3: statistics ──────────────────────────────────────────────────────
class SampleSizeComputation(BaseModel):
    tool: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    interpretation: str


class StatisticalAnalysisPlan(BaseModel):
    primary_hypotheses: list[str]
    computations: list[SampleSizeComputation]
    final_sample_size: dict[str, Any] = Field(
        description="n_positive, n_negative, n_total, readers, cases_with_attrition …"
    )
    stratified_allocation: dict[str, Any] = Field(default_factory=dict)
    analysis_methods: list[str]
    handling_of_missing_and_indeterminate: str
    subgroup_analyses: list[str]
    sap_markdown: str = Field(
        description="Narrative SAP section text produced by the Biostatistician agent"
    )


# ── Stage 4: protocol sections ───────────────────────────────────────────────
SECTION_KEYS: list[tuple[str, str, str]] = [
    ("synopsis", "1. Protocol Synopsis", "計畫書摘要"),
    ("background", "2. Background, Rationale and Unmet Clinical Need", "研究背景與臨床未滿足需求"),
    ("objectives", "3. Objectives and Hypotheses", "試驗目的與假設"),
    (
        "device",
        "4. Investigational Device Description and Human–AI Workflow",
        "試驗醫材描述與人機協作流程",
    ),
    ("design", "5. Study Design", "整體研究設計"),
    (
        "eligibility",
        "6. Subject / Data Eligibility and Sampling Strategy",
        "受試者與資料納入排除及抽樣策略",
    ),
    ("ground_truth", "7. Reference Standard (Ground Truth) Establishment", "參考標準建立流程"),
    ("statistics", "8. Statistical Analysis Plan and Sample Size", "統計分析計畫與樣本數推算"),
    (
        "data_management",
        "9. Data Management, De-identification and Information Security",
        "資料管理、去識別化與資安規範",
    ),
    (
        "ethics",
        "10. Ethical Considerations and IRB / Regulatory Compliance",
        "倫理考量與人體試驗委員會規範",
    ),
]


class DraftSection(BaseModel):
    key: str
    title_en: str
    title_zh: str
    markdown: str
    citations: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    revision: int = 1
    last_edited_by: str = "writer_agent"


# ── Stage 5: audit ───────────────────────────────────────────────────────────
class AuditItemResult(BaseModel):
    checklist_id: str
    item_id: str
    item_text: str
    status: str = Field(description="pass | partial | fail | not_applicable")
    evidence_sections: list[str] = Field(default_factory=list)
    finding: str = ""
    fix_suggestion: str | None = None


class AuditReport(BaseModel):
    iteration: int
    checklists_audited: list[str]
    items: list[AuditItemResult]
    n_pass: int
    n_partial: int
    n_fail: int
    n_not_applicable: int
    overall_verdict: str
    revision_requests: dict[str, list[str]] = Field(
        default_factory=dict, description="section_key → list of fixes"
    )


# ── Whole run ────────────────────────────────────────────────────────────────
class RunState(BaseModel):
    run_id: str
    project_id: str
    stage: RunStage = RunStage.created
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    error: str | None = None
    triage: TriageDecision | None = None
    evidence: EvidenceMatrix | None = None
    sap: StatisticalAnalysisPlan | None = None
    sections: list[DraftSection] = Field(default_factory=list)
    audits: list[AuditReport] = Field(default_factory=list)
    llm_calls: int = 0
    tool_calls: int = 0
    warnings: list[str] = Field(default_factory=list)

    def section(self, key: str) -> DraftSection | None:
        return next((s for s in self.sections if s.key == key), None)


class EvidenceConfirmation(BaseModel):
    accepted_ref_ids: list[str] | None = Field(
        default=None,
        description="If given, only these items are kept; otherwise all current `accepted` flags are honoured",
    )
    item_notes: dict[str, str] = Field(default_factory=dict)
    reviewer_notes: str | None = None
    baseline_overrides: dict[str, float] = Field(
        default_factory=dict,
        description="Manual overrides, e.g. {'unaided_reader_sensitivity': 0.84}",
    )


class SectionEdit(BaseModel):
    markdown: str
    editor: str = "user"
