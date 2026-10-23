"""Stage 1 — Regulatory Triage Agent."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.protocol_input import DataCollectionMode, DesignType, Jurisdiction
from ..schemas.run import RunStage, TriageDecision
from .base import AgentContext, compact_json

ARCHETYPE = {
    DesignType.Standalone_Performance: "standalone_diagnostic_accuracy",
    DesignType.MRMC_Reader_Study: "mrmc_reader_study",
    DesignType.Hybrid_Standalone_and_MRMC: "hybrid",
    DesignType.Prospective_Interventional_RCT: "prospective_interventional",
}

PATHWAY = {
    Jurisdiction.TFDA: "TFDA 醫療器材查驗登記 (醫療器材管理法) — AI/ML SaMD technical guidance (2020)",
    Jurisdiction.US_FDA_510k: "US FDA 510(k) premarket notification with predicate comparison",
    Jurisdiction.US_FDA_DeNovo: "US FDA De Novo classification request (no predicate)",
    Jurisdiction.US_FDA_PMA: "US FDA Premarket Approval (Class III)",
    Jurisdiction.CE_MDR: "EU MDR 2017/745 conformity assessment (MDCG 2020-1 clinical evaluation of software)",
    Jurisdiction.Other: "Other jurisdiction — confirm local requirements",
}


class TriageNarrative(BaseModel):
    significant_risk_assessment: str = Field(
        description="Reasoned assessment of risk category for IRB/regulatory planning, citing the supplied guideline excerpts"
    )
    key_regulatory_considerations: list[str] = Field(min_length=3)
    recommended_statistical_framework: str
    rationale: str


def rag_jurisdictions(jurs: list[Jurisdiction]) -> list[str]:
    out: list[str] = []
    for j in jurs:
        if j == Jurisdiction.TFDA:
            out.append("TW")
        elif j in (Jurisdiction.US_FDA_510k, Jurisdiction.US_FDA_DeNovo, Jurisdiction.US_FDA_PMA):
            out.append("US")
        elif j == Jurisdiction.CE_MDR:
            out.append("EU")
    out.append("INTL")
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def deterministic_facts(ctx: AgentContext) -> dict:
    d = ctx.input.study_design
    dp = ctx.input.device_profile
    retro = d.data_collection_mode == DataCollectionMode.Retrospective
    if d.design_type == DesignType.Prospective_Interventional_RCT:
        risk_hint = (
            "Prospective interventional use of the AI output in patient management: assess as a potentially "
            "significant-risk device study; full IRB review and (TFDA) 醫療器材臨床試驗申請 likely required unless the "
            "design falls within a published non-significant-risk category."
        )
    elif retro:
        risk_hint = (
            "Retrospective evaluation on de-identified existing data with no influence on patient care: typically "
            "non-significant-risk / 無顯著風險 (TFDA 醫療器材管理法 §37 公告態樣); IRB approval still required, "
            "informed-consent waiver may be requested."
        )
    else:
        risk_hint = (
            "Prospective data collection without AI output influencing care (silent-mode / reader study): usually "
            "non-significant-risk, but prospective enrolment needs consent procedures and site IRB approval."
        )
    return {
        "study_archetype": ARCHETYPE[d.design_type],
        "regulatory_pathways": [PATHWAY[j] for j in dp.target_jurisdictions],
        "risk_hint": risk_hint,
        "algorithm_type": ctx.input.ai_specifications.algorithm_type.value,
        "human_ai_workflow": ctx.input.ai_specifications.human_ai_workflow.value,
        "clinical_role": dp.indications_for_use.clinical_role.value,
    }


async def run_triage(ctx: AgentContext) -> TriageDecision:
    facts = deterministic_facts(ctx)
    dp = ctx.input.device_profile
    checklists = (
        await ctx.mcp.try_call(
            "regulatory_rag",
            "select_checklists",
            {
                "design_type": ctx.input.study_design.design_type.value,
                "samd_category": dp.samd_category.value,
                "jurisdictions": [j.value for j in dp.target_jurisdictions],
            },
            default=[],
            warnings=ctx.state.warnings,
        )
        or []
    )
    query = (
        f"clinical performance study design requirements for {dp.samd_category.value} {ctx.input.ai_specifications.input_modality} "
        f"{ctx.input.study_design.design_type.value} reference standard sample size"
    )
    clauses: list[dict] = []
    for jur in rag_jurisdictions(dp.target_jurisdictions):
        res = await ctx.mcp.try_call(
            "regulatory_rag",
            "retrieve_guideline_clauses",
            {"query": query, "jurisdiction": jur, "top_k": 4},
            default=None,
            warnings=ctx.state.warnings,
        )
        if res and res.get("results"):
            clauses.extend(res["results"])
    await ctx.progress(
        "Triage: checklists selected",
        checklists=[c.get("checklist_id") for c in checklists],
        clauses=len(clauses),
    )

    system = ctx.system_prompt(
        "ROLE: Regulatory Triage Agent. Classify the regulatory and methodological pathway for the study. "
        "Do not restate the inputs; reason about risk category, pathway-specific evidence expectations and the "
        "statistical framework (performance-goal vs. comparative; standalone vs. MRMC OR-model; superiority/NI)."
    )
    user = (
        "SPONSOR INPUT (JSON):\n"
        + compact_json(ctx.input, 6000)
        + "\n\nDETERMINISTIC FACTS:\n"
        + compact_json(facts)
        + "\n\nAPPLICABLE CHECKLISTS (from mcp-regulatory-rag):\n"
        + compact_json(checklists, 3000)
        + "\n\nGUIDELINE EXCERPTS:\n"
        + compact_json(
            [{"citation": c.get("citation"), "text": c.get("text")} for c in clauses], 8000
        )
        + "\n\nProduce the triage narrative."
    )
    narrative = await ctx.ask_json(system=system, user=user, model=TriageNarrative)
    decision = TriageDecision(
        study_archetype=facts["study_archetype"],
        regulatory_pathways=facts["regulatory_pathways"],
        applicable_checklists=[
            {
                "checklist_id": str(c.get("checklist_id")),
                "role": str(c.get("role")),
                "rationale": str(c.get("rationale")),
            }
            for c in checklists
        ],
        significant_risk_assessment=narrative.significant_risk_assessment,
        key_regulatory_considerations=narrative.key_regulatory_considerations,
        recommended_statistical_framework=narrative.recommended_statistical_framework,
        rationale=narrative.rationale,
    )
    await ctx.log("Triage complete", RunStage.triage, archetype=decision.study_archetype)
    return decision
