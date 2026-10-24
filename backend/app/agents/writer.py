"""Stage 4 — Protocol Writer Agent: ten sections drafted in parallel with RAG context."""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from ..schemas.run import (
    SECTION_KEYS,
    DraftSection,
    EvidenceMatrix,
    StatisticalAnalysisPlan,
    TriageDecision,
)
from .base import AgentContext, compact_json, truncate
from .triage import rag_jurisdictions


class SectionDraftOut(BaseModel):
    markdown: str = Field(
        description="Section body in Markdown (no top-level H1; use ### for sub-headings)"
    )
    citations: list[str] = Field(
        description="Citation strings actually used, copied verbatim from the supplied evidence/guidance"
    )
    open_questions: list[str] = Field(
        description="Items the sponsor must confirm, marked [TO BE CONFIRMED] in the text"
    )


# What each section must cover, and the retrieval query used to fetch guidance for it.
SECTION_GUIDE: dict[str, dict[str, Any]] = {
    "synopsis": {
        "must": [
            "title stating AI/ML model type and intended use (SPIRIT-AI 1(i)/(ii), STARD-AI title)",
            "one-table synopsis: device/version, design, population, sites, sample size, primary endpoints & goals, reference standard, duration",
            "sponsor / PI / protocol ID placeholders",
        ],
        "query": "protocol synopsis required elements clinical investigation plan",
        "ctx": ["sap", "evidence"],
    },
    "background": {
        "must": [
            "clinical problem and unmet need with literature baseline (unaided performance)",
            "intended use in the clinical pathway and intended users (SPIRIT-AI 6a(i))",
            "pre-existing evidence for the device and predicates (SPIRIT-AI 6a(ii)); IMDRF N41 pillars addressed",
            "regulatory context per jurisdiction",
        ],
        "query": "valid clinical association pre-existing evidence intended use clinical pathway",
        "ctx": ["evidence", "triage"],
    },
    "objectives": {
        "must": [
            "primary objective(s) and formal hypotheses (H0/H1) with performance goals or comparator",
            "secondary objectives (PPV/NPV, subgroups, reader time)",
            "exploratory objectives (error analysis, calibration)",
        ],
        "query": "primary endpoint hypothesis performance goal sensitivity specificity",
        "ctx": ["sap"],
    },
    "device": {
        "must": [
            "algorithm version & locked status (SPIRIT-AI 11a(i))",
            "input data acquisition/selection and quality requirements, handling of poor-quality/unprocessable inputs (11a(ii)-(iii))",
            "output and operating point (11a(v))",
            "human–AI interaction, user expertise and training (11a(iv))",
            "how output contributes to decisions / workflow (11a(vi))",
            "deployment, IT integration, on/offsite requirements (SPIRIT-AI 9)",
            "training data summary and test-set independence",
        ],
        "query": "software version input data quality poor quality unavailable input human AI interaction output",
        "ctx": ["evidence"],
    },
    "design": {
        "must": [
            "design type with rationale vs predicates (standalone / MRMC fully-crossed with washout / RCT)",
            "data collection mode, sites, enrichment and prevalence",
            "reading procedure, randomisation of case order, blinding",
            "schedule / study flow diagram description",
            "bias minimisation and data independence",
        ],
        "query": "fully crossed MRMC reader study washout standalone performance study design retrospective",
        "ctx": ["evidence", "sap", "triage"],
    },
    "eligibility": {
        "must": [
            "participant-level inclusion/exclusion (SPIRIT-AI 10(i))",
            "data/image-level inclusion/exclusion: devices, protocols, quality (10(ii))",
            "sampling strategy, case enrichment, consecutive vs random, target prevalence",
            "subgroup stratification plan and minimum representation",
            "data sources and time windows; multi-image per patient handling",
        ],
        "query": "inclusion exclusion criteria input data level sampling enrichment intended use population spectrum",
        "ctx": ["evidence", "sap"],
    },
    "ground_truth": {
        "must": [
            "reference standard definition and rationale",
            "adjudicator number, qualifications, independence, blinding to AI",
            "truthing workflow, disagreement adjudication, inter-rater variability reporting",
            "handling of indeterminate truth",
        ],
        "query": "reference standard truthing adjudication expert panel blinding",
        "ctx": ["evidence"],
    },
    "statistics": {
        "must": [
            "reproduce the SAP faithfully from the supplied sap_markdown and computations",
            "sample size derivation table",
            "analysis populations, missing/indeterminate handling",
            "subgroup & error analysis (SPIRIT-AI 22(ii), STARD-AI AI-11)",
        ],
        "query": "statistical analysis sample size justification variance components confidence interval",
        "ctx": ["sap"],
    },
    "data_management": {
        "must": [
            "de-identification / pseudonymisation per 個人資料保護法 & HIPAA (as applicable)",
            "data flow, storage, access control, audit trail, retention",
            "software validation, version control, device accountability (ISO 14155 A.13)",
            "data quality assurance and monitoring",
            "code/model access statement (SPIRIT-AI 29(ii))",
        ],
        "query": "data management de-identification cybersecurity record retention",
        "ctx": [],
    },
    "ethics": {
        "must": [
            "IRB/REC approval, risk category (無顯著風險 / NSR) with justification",
            "informed consent or waiver justification",
            "compliance statements: ISO 14155, Declaration of Helsinki, 醫療器材優良臨床試驗作業規範, 人體研究法",
            "adverse event / device deficiency reporting incl. erroneous output",
            "registration, publication policy, conflicts of interest",
        ],
        "query": "informed consent waiver retrospective non-significant risk IRB device deficiency reporting",
        "ctx": ["triage"],
    },
}


def _evidence_context(ev: EvidenceMatrix | None, limit: int = 9000) -> str:
    if not ev:
        return "(no evidence available)"
    accepted = [
        {
            k: v
            for k, v in i.model_dump(mode="json").items()
            if k
            in (
                "source",
                "ref_id",
                "title",
                "design",
                "sample_size",
                "readers",
                "endpoints",
                "reported_performance",
                "ground_truth",
                "summary",
            )
            and v not in (None, [], {}, "")
        }
        for i in ev.items
        if i.accepted
    ]
    return compact_json(
        {
            "benchmark_rows": ev.benchmark_rows,
            "baseline_performance": ev.baseline_performance,
            "narrative": ev.narrative_summary,
            "reviewer_notes": ev.reviewer_notes,
            "accepted_items": accepted,
        },
        limit,
    )


def _sap_context(sap: StatisticalAnalysisPlan | None, full: bool) -> str:
    if not sap:
        return "(SAP not available)"
    if full:
        return compact_json(
            {
                "final_sample_size": sap.final_sample_size,
                "hypotheses": sap.primary_hypotheses,
                "methods": sap.analysis_methods,
                "computations": [
                    {
                        "tool": c.tool,
                        "inputs": c.inputs,
                        "outputs": c.outputs,
                        "interpretation": c.interpretation,
                    }
                    for c in sap.computations
                ],
                "stratified_allocation": sap.stratified_allocation,
                "sap_markdown": sap.sap_markdown,
            },
            16000,
        )
    return compact_json(
        {
            "final_sample_size": sap.final_sample_size,
            "hypotheses": sap.primary_hypotheses,
            "methods": sap.analysis_methods,
        },
        3000,
    )


async def _guidance(ctx: AgentContext, query: str) -> list[dict]:
    out: list[dict] = []
    for jur in rag_jurisdictions(ctx.input.device_profile.target_jurisdictions)[:3]:
        res = await ctx.mcp.try_call(
            "regulatory_rag",
            "retrieve_guideline_clauses",
            {"query": query, "jurisdiction": jur, "top_k": 3},
            warnings=ctx.state.warnings,
        )
        out.extend((res or {}).get("results") or [])
    return [
        {"citation": r.get("citation"), "text": truncate(r.get("text") or "", 700)} for r in out[:8]
    ]


async def draft_section(
    ctx: AgentContext,
    key: str,
    *,
    triage: TriageDecision | None,
    evidence: EvidenceMatrix | None,
    sap: StatisticalAnalysisPlan | None,
) -> DraftSection:
    title_en, title_zh = next((e, z) for k, e, z in SECTION_KEYS if k == key)
    guide = SECTION_GUIDE[key]
    guidance = await _guidance(
        ctx, f"{guide['query']} {ctx.input.device_profile.samd_category.value}"
    )
    parts = [
        f"SECTION TO WRITE: {title_zh} / {title_en}",
        "MUST COVER:\n- " + "\n- ".join(guide["must"]),
        "SPONSOR INPUT (JSON):\n" + compact_json(ctx.input, 7000),
    ]
    if "triage" in guide["ctx"] and triage:
        parts.append("REGULATORY TRIAGE:\n" + compact_json(triage, 3000))
    if "evidence" in guide["ctx"]:
        parts.append(
            "EVIDENCE (confirmed by the sponsor's reviewer):\n" + _evidence_context(evidence)
        )
    if "sap" in guide["ctx"]:
        parts.append("STATISTICAL ANALYSIS PLAN:\n" + _sap_context(sap, full=(key == "statistics")))
    parts.append("GUIDANCE EXCERPTS (cite by citation string):\n" + compact_json(guidance, 6000))
    parts.append(
        "Write the section body now. Use [TO BE CONFIRMED: …] for anything not supported by the inputs."
    )
    system = ctx.system_prompt(
        "ROLE: Protocol Writer Agent. Write ONE section of a medical-device clinical investigation plan (ISO 14155 Annex A "
        "structure). Address every MUST COVER bullet explicitly (use sub-headings), keep sponsor-provided values exact, and never "
        "introduce numbers that are not in the SAP or the sponsor input. Length: 400–1200 words depending on the section."
    )
    out = await ctx.ask_json(
        system=system,
        user="\n\n".join(parts),
        model=SectionDraftOut,
        max_tokens=ctx.settings.llm_section_max_tokens,
    )
    return DraftSection(
        key=key,
        title_en=title_en,
        title_zh=title_zh,
        markdown=out.markdown,
        citations=out.citations,
        open_questions=out.open_questions,
    )


def placeholder_section(key: str, error: str) -> DraftSection:
    title_en, title_zh = next((e, z) for k, e, z in SECTION_KEYS if k == key)
    return DraftSection(
        key=key,
        title_en=title_en,
        title_zh=title_zh,
        markdown=(
            "> ⚠️ 本章節自動撰寫失敗，請按「重新執行」或手動撰寫。 / Automatic drafting of this section failed; "
            f"re-run or write it manually.\n>\n> Error: `{error[:300]}`\n\n[TO BE CONFIRMED: section not generated]"
        ),
        citations=[],
        open_questions=[
            "Section was not generated by the model; needs manual drafting or a re-run."
        ],
        last_edited_by="writer_agent(failed)",
    )


async def run_writer(
    ctx: AgentContext,
    *,
    triage: TriageDecision | None,
    evidence: EvidenceMatrix | None,
    sap: StatisticalAnalysisPlan | None,
) -> list[DraftSection]:
    sem = asyncio.Semaphore(max(1, ctx.settings.writer_concurrency))
    results: dict[str, DraftSection] = {}

    async def one(key: str) -> None:
        async with sem:
            await ctx.progress(f"Writing section: {key}")
            try:
                results[key] = await draft_section(
                    ctx, key, triage=triage, evidence=evidence, sap=sap
                )
            except Exception as exc:  # one failed section must not sink the whole run
                msg = f"section '{key}' could not be generated: {type(exc).__name__}: {str(exc)[:300]}"
                ctx.state.warnings.append(msg)
                await ctx.log(msg)
                results[key] = placeholder_section(key, str(exc))

    await asyncio.gather(*(one(k) for k, _, _ in SECTION_KEYS))
    return [results[k] for k, _, _ in SECTION_KEYS]


async def revise_section(
    ctx: AgentContext,
    section: DraftSection,
    fixes: list[str],
    *,
    sap: StatisticalAnalysisPlan | None,
) -> DraftSection:
    system = ctx.system_prompt(
        "ROLE: Protocol Writer Agent (revision mode). Apply the audit fixes to the section with minimal, surgical edits; keep all "
        "existing numbers and citations unless a fix says otherwise; do not shorten unrelated content."
    )
    user = (
        f"SECTION: {section.title_zh} / {section.title_en}\n\nCURRENT TEXT (Markdown):\n{section.markdown}\n\nAUDIT FIXES REQUIRED:\n- "
        + "\n- ".join(fixes)
        + "\n\nSPONSOR INPUT (JSON):\n"
        + compact_json(ctx.input, 5000)
        + (
            "\n\nSAP SUMMARY:\n" + _sap_context(sap, full=(section.key == "statistics"))
            if sap
            else ""
        )
        + "\n\nReturn the full revised section."
    )
    out = await ctx.ask_json(
        system=system,
        user=user,
        model=SectionDraftOut,
        max_tokens=ctx.settings.llm_section_max_tokens,
    )
    return DraftSection(
        key=section.key,
        title_en=section.title_en,
        title_zh=section.title_zh,
        markdown=out.markdown,
        citations=sorted(set(section.citations) | set(out.citations)),
        open_questions=out.open_questions,
        revision=section.revision + 1,
        last_edited_by="writer_agent(revision)",
    )
