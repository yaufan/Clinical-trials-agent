"""Stage 3 — Biostatistician Agent: deterministic sample size via mcp-biostat-calc + SAP narrative."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..schemas.protocol_input import DesignType, HypothesisType
from ..schemas.run import EvidenceMatrix, RunStage, SampleSizeComputation, StatisticalAnalysisPlan
from .base import AgentContext, compact_json

ILLUSTRATIVE_OR_COMPONENTS = {
    "var_treatment_reader": 0.0005,
    "var_error": 0.0020,
    "cov1": 0.0008,
    "cov2": 0.0007,
    "cov3": 0.0004,
    "pilot_cases": 100,
}


class SAPNarrative(BaseModel):
    primary_hypotheses: list[str] = Field(min_length=1)
    analysis_methods: list[str] = Field(min_length=2)
    handling_of_missing_and_indeterminate: str
    subgroup_analyses: list[str]
    computation_interpretations: list[str] = Field(
        description="One sentence per computation, same order as supplied"
    )
    sap_markdown: str = Field(
        description="Full SAP section text in Markdown using ONLY the supplied numbers"
    )


def _num(d: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        v = d.get(k)
        if isinstance(v, int | float) and 0 < float(v) < 1:
            return float(v)
    return None


async def run_biostat(
    ctx: AgentContext, evidence: EvidenceMatrix | None
) -> StatisticalAnalysisPlan:
    inp = ctx.input
    sa, sd = inp.statistical_assumptions, inp.study_design
    one_sided = sa.alpha_sidedness == "one_sided"
    baseline = (evidence.baseline_performance if evidence else {}) or {}
    comps: list[SampleSizeComputation] = []
    final: dict[str, Any] = {}
    W = ctx.state.warnings
    design = sd.design_type

    async def compute(tool: str, args: dict[str, Any], label: str) -> dict[str, Any] | None:
        res = await ctx.mcp.try_call("biostat", tool, args, warnings=W)
        if res is None:
            W.append(f"biostat.{tool} unavailable — {label} not computed")
            return None
        comps.append(
            SampleSizeComputation(tool=tool, inputs=args, outputs=res, interpretation=label)
        )
        return res

    # ── standalone / hybrid: sensitivity & specificity performance goals ─────
    if design in (DesignType.Standalone_Performance, DesignType.Hybrid_Standalone_and_MRMC):
        if sa.expected_sensitivity or sa.expected_specificity:
            args = {
                "expected_sensitivity": sa.expected_sensitivity,
                "sensitivity_goal": sa.sensitivity_goal,
                "expected_specificity": sa.expected_specificity,
                "specificity_goal": sa.specificity_goal,
                "alpha": sa.alpha,
                "power": sa.power,
                "one_sided": one_sided,
                "method": "exact_binomial",
                "attrition_rate": sa.expected_attrition_rate,
                "prevalence": sd.target_prevalence_in_study,
            }
            res = await compute(
                "calc_standalone_sample_size",
                {k: v for k, v in args.items() if v is not None},
                "Co-primary sensitivity/specificity vs performance goals (exact binomial)",
            )
            if res:
                final.update(
                    n_positive=res.get("n_positive_with_attrition"),
                    n_negative=res.get("n_negative_with_attrition"),
                    n_total=res.get("n_total_with_attrition"),
                    n_positive_evaluable=res.get("n_positive"),
                    n_negative_evaluable=res.get("n_negative"),
                    n_total_at_prevalence=res.get("n_total_at_prevalence"),
                )
        if sa.expected_sensitivity and sa.expected_specificity and sd.target_prevalence_in_study:
            await compute(
                "calc_buderer_sample_size",
                {
                    "expected_sensitivity": sa.expected_sensitivity,
                    "expected_specificity": sa.expected_specificity,
                    "prevalence": sd.target_prevalence_in_study,
                    "ci_halfwidth_sensitivity": 0.05,
                    "ci_halfwidth_specificity": 0.05,
                    "alpha": 0.05,
                    "attrition_rate": sa.expected_attrition_rate,
                },
                "Precision cross-check (Buderer 1996, ±5 % CI half-width)",
            )
        if sa.expected_auc and sa.auc_goal:
            res = await compute(
                "calc_auc_sample_size",
                {
                    "expected_auc": sa.expected_auc,
                    "auc_goal": sa.auc_goal,
                    "alpha": sa.alpha,
                    "power": sa.power,
                    "one_sided": one_sided,
                    "negative_to_positive_ratio": (
                        (1 - sd.target_prevalence_in_study) / sd.target_prevalence_in_study
                    )
                    if sd.target_prevalence_in_study
                    else 1.0,
                    "attrition_rate": sa.expected_attrition_rate,
                },
                "AUROC vs performance goal (Hanley–McNeil)",
            )
            if res and not final.get("n_total"):
                final.update(
                    n_positive=res.get("n_positive"),
                    n_negative=res.get("n_negative"),
                    n_total=res.get("n_total_with_attrition"),
                )

    # ── MRMC / hybrid: Obuchowski–Rockette power ─────────────────────────────
    if (
        design in (DesignType.MRMC_Reader_Study, DesignType.Hybrid_Standalone_and_MRMC)
        and sd.mrmc_config
    ):
        readers = sd.mrmc_config.total_readers
        delta = sa.mrmc_effect_size_delta_auc
        if delta is None:
            delta = 0.05
            W.append(
                "mrmc_effect_size_delta_auc not provided — assumed ΔAUC = 0.05 (placeholder, confirm with sponsor)"
            )
        if sa.pilot_variance_components:
            comps_vc = sa.pilot_variance_components.model_dump()
            illustrative = False
        else:
            comps_vc = dict(ILLUSTRATIVE_OR_COMPONENTS)
            illustrative = True
            W.append(
                "No pilot OR-model variance components supplied — MRMC power uses ILLUSTRATIVE components; "
                "replace with pilot-study estimates (RJafroc/iMRMC) before finalising the protocol."
            )
        args = {
            "readers": readers,
            "effect_size": delta,
            **comps_vc,
            "alpha": 0.05 if one_sided and sa.alpha == 0.025 else sa.alpha,
            "power": sa.power,
            "attrition_rate": sa.expected_attrition_rate,
        }
        res = await compute(
            "calc_mrmc_sample_size",
            args,
            ("ILLUSTRATIVE — " if illustrative else "")
            + f"MRMC cases for {readers} readers, ΔAUC={delta} (OR model, Hillis ddf)",
        )
        if res:
            final.update(
                readers=readers,
                mrmc_cases=res.get("cases_required"),
                mrmc_cases_with_attrition=res.get("cases_with_attrition"),
                mrmc_power=res.get("achieved_power"),
                mrmc_components_illustrative=illustrative,
            )
            if res.get("max_power_at_limit") is not None:
                W.append(
                    "Target MRMC power unattainable by adding cases; increase readers (see reader/case grid)."
                )
        await compute(
            "calc_mrmc_reader_case_grid",
            {
                "effect_size": delta,
                **comps_vc,
                "reader_counts": sorted({max(4, readers - 4), readers, readers + 4, readers + 8}),
                "alpha": args["alpha"],
                "power": sa.power,
            },
            "Reader/case trade-off grid",
        )
        p_ref = _num(baseline, "unaided_reader_sensitivity", "reader_sensitivity_without_ai")
        if sa.expected_sensitivity and p_ref and sa.expected_sensitivity > p_ref:
            await compute(
                "calc_paired_proportion_sample_size",
                {
                    "p_test": sa.expected_sensitivity,
                    "p_reference": p_ref,
                    "alpha": sa.alpha,
                    "power": sa.power,
                    "one_sided": one_sided,
                    "attrition_rate": sa.expected_attrition_rate,
                },
                "Secondary: reader sensitivity with vs without AI on the same cases (McNemar / Connor)",
            )

    # ── prospective RCT: two independent arms ────────────────────────────────
    if design == DesignType.Prospective_Interventional_RCT:
        p_ref = _num(baseline, "unaided_reader_sensitivity", "standard_care_rate", "control_rate")
        if p_ref is None:
            p_ref = sa.sensitivity_goal or 0.80
            W.append(
                f"No control-arm baseline in the evidence — assumed p_reference={p_ref} (confirm)"
            )
        p_test = sa.expected_sensitivity or min(0.99, p_ref + 0.1)
        ni = sa.hypothesis_type == HypothesisType.Non_Inferiority
        margin = sa.non_inferiority_margin or (0.05 if ni else 0.0)
        if ni and sa.non_inferiority_margin is None:
            W.append("Non-inferiority margin not provided — assumed 0.05")
        res = await compute(
            "calc_two_proportion_sample_size",
            {
                "p_test": p_test,
                "p_reference": p_ref,
                "alpha": sa.alpha,
                "power": sa.power,
                "one_sided": one_sided,
                "hypothesis": "non_inferiority" if ni else "superiority",
                "margin": margin,
                "allocation_ratio": 1.0,
                "attrition_rate": sa.expected_attrition_rate,
            },
            "Primary endpoint, two parallel arms",
        )
        if res:
            final.update(
                n_test_arm=res.get("n_test"),
                n_reference_arm=res.get("n_reference"),
                n_total=res.get("n_total_with_attrition"),
            )

    # ── stratified allocation across sites ───────────────────────────────────
    strat: dict[str, Any] = {}
    total_for_alloc = final.get("n_total") or final.get("mrmc_cases_with_attrition")
    if total_for_alloc and sd.study_sites_count > 1:
        props = {f"Site {i + 1}": 1.0 / sd.study_sites_count for i in range(sd.study_sites_count)}
        res = await compute(
            "allocate_strata",
            {"total": int(total_for_alloc), "proportions": props},
            "Equal allocation across study sites",
        )
        if res:
            strat["by_site"] = res.get("allocation")
    if total_for_alloc and sd.subgroup_stratification:
        strat["planned_subgroups"] = sd.subgroup_stratification
        strat["note"] = (
            "Subgroup sizes follow natural distribution; each pre-specified subgroup should retain ≥ 30 positives where feasible (descriptive precision only)."
        )

    await ctx.progress("Biostat: computations done", n=len(comps))

    system = ctx.system_prompt(
        "ROLE: Biostatistician Agent. Write the Statistical Analysis Plan (SAP) section of the protocol strictly from the "
        "supplied tool outputs. Report: hypotheses (H0/H1 with alpha and sidedness), primary analysis (exact binomial / Wilson "
        "CI vs performance goal; OR-model MRMC F-test with Hillis ddf; McNemar; two-proportion test), sample size derivation "
        "with every number traceable to a computation, attrition inflation, analysis populations, handling of unevaluable / "
        "indeterminate AI outputs and missing reference standard, multiplicity (co-primary intersection-union), subgroup "
        "analyses, and interim/stopping rules (usually none for retrospective designs). Flag illustrative placeholders loudly."
    )
    user = (
        "SPONSOR STATISTICAL ASSUMPTIONS & DESIGN:\n"
        + compact_json({"statistical_assumptions": sa, "study_design": sd}, 4000)
        + "\n\nBASELINE PERFORMANCE FROM EVIDENCE:\n"
        + compact_json(baseline, 1500)
        + "\n\nCOMPUTATIONS (tool, inputs, outputs):\n"
        + compact_json([c.model_dump() for c in comps], 14000)
        + "\n\nFINAL SAMPLE SIZE SUMMARY:\n"
        + compact_json(final)
        + "\n\nSTRATIFIED ALLOCATION:\n"
        + compact_json(strat, 1500)
        + "\n\nWARNINGS TO DISCLOSE:\n"
        + compact_json(W[-8:])
        + "\n\nWrite the SAP."
    )
    narrative = await ctx.ask_json(system=system, user=user, model=SAPNarrative, max_tokens=6000)
    for c, interp in zip(comps, narrative.computation_interpretations, strict=False):
        c.interpretation = f"{c.interpretation} — {interp}"
    sap = StatisticalAnalysisPlan(
        primary_hypotheses=narrative.primary_hypotheses,
        computations=comps,
        final_sample_size=final,
        stratified_allocation=strat,
        analysis_methods=narrative.analysis_methods,
        handling_of_missing_and_indeterminate=narrative.handling_of_missing_and_indeterminate,
        subgroup_analyses=narrative.subgroup_analyses,
        sap_markdown=narrative.sap_markdown,
    )
    await ctx.log("SAP complete", RunStage.biostat, final=final)
    return sap
