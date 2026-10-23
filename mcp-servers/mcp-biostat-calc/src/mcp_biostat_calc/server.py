"""MCP tool surface for mcp-biostat-calc (official MCP Python SDK 2.x, ``MCPServer``)."""

from __future__ import annotations

from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import core


def _call(fn, /, *args, **kwargs):
    """Run a core function, surfacing input errors as MCP tool errors (not server crashes)."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, ZeroDivisionError, RuntimeError) as exc:
        raise ToolError(str(exc)) from exc


INSTRUCTIONS = """Deterministic biostatistics for AI-SaMD clinical study design.
Use these tools instead of estimating sample sizes yourself. Conventions:
- alpha is the overall type-I error for the stated sidedness (one_sided=True → one-sided alpha,
  e.g. 0.025 is the FDA performance-goal convention).
- Sensitivity/specificity designs count *evaluable* positive and negative cases; the
  *_with_attrition fields inflate for unevaluable cases.
- MRMC tools implement the Obuchowski–Rockette / Hillis (2011) F-test and need pilot
  variance components; use calc_mrmc_reader_case_grid to show reader/case trade-offs.
Always report the method, assumptions and the formula reference returned in `notes`."""

server = MCPServer(
    name="mcp-biostat-calc",
    title="Biostatistics Calculator (AI-SaMD)",
    instructions=INSTRUCTIONS,
    version="0.1.0",
)


@server.tool(
    description=(
        "Positive/negative case counts for a standalone performance study with sensitivity "
        "and/or specificity performance goals (one-sample proportion tests; exact binomial by default)."
    )
)
def calc_standalone_sample_size(
    expected_sensitivity: float | None = None,
    sensitivity_goal: float | None = None,
    expected_specificity: float | None = None,
    specificity_goal: float | None = None,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    method: Literal["normal", "exact_binomial"] = "exact_binomial",
    attrition_rate: float = 0.10,
    prevalence: float | None = None,
) -> core.StandaloneSampleSize:
    return _call(
        core.standalone_sample_size,
        expected_sensitivity=expected_sensitivity,
        sensitivity_goal=sensitivity_goal,
        expected_specificity=expected_specificity,
        specificity_goal=specificity_goal,
        alpha=alpha,
        power=power,
        one_sided=one_sided,
        method=method,
        attrition_rate=attrition_rate,
        prevalence=prevalence,
    )


@server.tool(
    description=(
        "Single proportion vs. a performance goal (H0: p ≤ p0 vs H1: p > p0, or the mirrored "
        "lower-tail test when p1 < p0). Returns n, and for the exact design the critical number of successes."
    )
)
def calc_one_sample_proportion(
    p0: float,
    p1: float,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    method: Literal["normal", "exact_binomial"] = "exact_binomial",
) -> core.OneSampleProportionResult:
    return _call(
        core.one_sample_proportion_sample_size,
        p0,
        p1,
        alpha=alpha,
        power=power,
        one_sided=one_sided,
        method=method,
    )


@server.tool(
    description=(
        "Buderer (1996) precision-based sample size: positives/negatives so that sensitivity and "
        "specificity CIs reach a target half-width at a given disease prevalence."
    )
)
def calc_buderer_sample_size(
    expected_sensitivity: float,
    expected_specificity: float,
    prevalence: float,
    ci_halfwidth_sensitivity: float = 0.05,
    ci_halfwidth_specificity: float = 0.05,
    alpha: float = 0.05,
    attrition_rate: float = 0.10,
) -> core.BudererResult:
    return _call(
        core.buderer_sample_size,
        expected_sensitivity=expected_sensitivity,
        expected_specificity=expected_specificity,
        prevalence=prevalence,
        ci_halfwidth_sensitivity=ci_halfwidth_sensitivity,
        ci_halfwidth_specificity=ci_halfwidth_specificity,
        alpha=alpha,
        attrition_rate=attrition_rate,
    )


@server.tool(
    description="Confidence interval for a binomial proportion (Wilson, Clopper–Pearson or Wald)."
)
def calc_proportion_ci(
    successes: int,
    trials: int,
    alpha: float = 0.05,
    method: Literal["wilson", "clopper_pearson", "wald"] = "wilson",
) -> core.ProportionCI:
    return _call(core.proportion_ci, successes, trials, alpha=alpha, method=method)


@server.tool(
    description="Sensitivity, specificity, PPV, NPV (with Wilson CIs) from a 2×2 confusion table."
)
def calc_diagnostic_accuracy(
    tp: int, fp: int, fn: int, tn: int, alpha: float = 0.05
) -> core.DiagnosticAccuracy:
    return _call(core.diagnostic_accuracy_from_counts, tp, fp, fn, tn, alpha=alpha)


@server.tool(
    description=(
        "Two independent groups (e.g. prospective RCT, AI-assisted vs. standard care): "
        "superiority or non-inferiority on a proportion endpoint."
    )
)
def calc_two_proportion_sample_size(
    p_test: float,
    p_reference: float,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    hypothesis: Literal["superiority", "non_inferiority"] = "superiority",
    margin: float = 0.0,
    allocation_ratio: float = 1.0,
    attrition_rate: float = 0.10,
) -> core.TwoProportionResult:
    return _call(
        core.two_proportion_sample_size,
        p_test=p_test,
        p_reference=p_reference,
        alpha=alpha,
        power=power,
        one_sided=one_sided,
        hypothesis=hypothesis,
        margin=margin,
        allocation_ratio=allocation_ratio,
        attrition_rate=attrition_rate,
    )


@server.tool(
    description=(
        "Paired design on the same cases (McNemar / Connor 1987): e.g. reader sensitivity with vs. "
        "without AI, or standalone AI vs. the clinical reference on identical cases."
    )
)
def calc_paired_proportion_sample_size(
    p_test: float,
    p_reference: float,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    discordant_proportion: float | None = None,
    hypothesis: Literal["superiority", "non_inferiority"] = "superiority",
    margin: float = 0.0,
    attrition_rate: float = 0.10,
) -> core.PairedProportionResult:
    return _call(
        core.paired_proportion_sample_size,
        p_test=p_test,
        p_reference=p_reference,
        alpha=alpha,
        power=power,
        one_sided=one_sided,
        discordant_proportion=discordant_proportion,
        hypothesis=hypothesis,
        margin=margin,
        attrition_rate=attrition_rate,
    )


@server.tool(
    description=(
        "Cases for an AUROC endpoint (Hanley–McNeil variance): either a CI half-width "
        "(precision) or an AUC performance goal (hypothesis test)."
    )
)
def calc_auc_sample_size(
    expected_auc: float,
    auc_goal: float | None = None,
    ci_halfwidth: float | None = None,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    negative_to_positive_ratio: float = 1.0,
    attrition_rate: float = 0.10,
) -> core.AUCSampleSizeResult:
    return _call(
        core.auc_sample_size,
        expected_auc=expected_auc,
        auc_goal=auc_goal,
        ci_halfwidth=ci_halfwidth,
        alpha=alpha,
        power=power,
        one_sided=one_sided,
        negative_to_positive_ratio=negative_to_positive_ratio,
        attrition_rate=attrition_rate,
    )


@server.tool(
    description=(
        "Power of a fully-crossed MRMC reader study (Obuchowski–Rockette model, Hillis 2011 ddf) "
        "for given readers, cases, effect size and pilot variance components."
    )
)
def calc_mrmc_power(
    readers: int,
    cases: int,
    effect_size: float,
    var_treatment_reader: float,
    var_error: float,
    cov1: float,
    cov2: float,
    cov3: float,
    pilot_cases: int,
    alpha: float = 0.05,
) -> core.MRMCPowerResult:
    comps = core.ORVarianceComponents(
        var_treatment_reader=var_treatment_reader,
        var_error=var_error,
        cov1=cov1,
        cov2=cov2,
        cov3=cov3,
        pilot_cases=pilot_cases,
    )
    return _call(
        core.mrmc_power,
        readers=readers,
        cases=cases,
        effect_size=effect_size,
        components=comps,
        alpha=alpha,
    )


@server.tool(
    description=(
        "Smallest number of cases reaching target power in a fully-crossed MRMC study with a fixed "
        "reader panel (Obuchowski–Rockette / Hillis)."
    )
)
def calc_mrmc_sample_size(
    readers: int,
    effect_size: float,
    var_treatment_reader: float,
    var_error: float,
    cov1: float,
    cov2: float,
    cov3: float,
    pilot_cases: int,
    alpha: float = 0.05,
    power: float = 0.80,
    attrition_rate: float = 0.10,
    max_cases: int = 5000,
) -> core.MRMCSampleSizeResult:
    comps = core.ORVarianceComponents(
        var_treatment_reader=var_treatment_reader,
        var_error=var_error,
        cov1=cov1,
        cov2=cov2,
        cov3=cov3,
        pilot_cases=pilot_cases,
    )
    return _call(
        core.mrmc_cases_needed,
        readers=readers,
        effect_size=effect_size,
        components=comps,
        alpha=alpha,
        power=power,
        attrition_rate=attrition_rate,
        max_cases=max_cases,
    )


@server.tool(description="Readers-vs-cases trade-off table for an MRMC study at target power.")
def calc_mrmc_reader_case_grid(
    effect_size: float,
    var_treatment_reader: float,
    var_error: float,
    cov1: float,
    cov2: float,
    cov3: float,
    pilot_cases: int,
    reader_counts: list[int] | None = None,
    alpha: float = 0.05,
    power: float = 0.80,
    max_cases: int = 5000,
) -> core.MRMCReaderCaseGrid:
    comps = core.ORVarianceComponents(
        var_treatment_reader=var_treatment_reader,
        var_error=var_error,
        cov1=cov1,
        cov2=cov2,
        cov3=cov3,
        pilot_cases=pilot_cases,
    )
    return _call(
        core.mrmc_reader_case_grid,
        effect_size=effect_size,
        components=comps,
        reader_counts=reader_counts or [4, 6, 8, 10, 12, 16, 20],
        alpha=alpha,
        power=power,
        max_cases=max_cases,
    )


@server.tool(description="Inflate a sample size for an expected attrition / unevaluable-case rate.")
def adjust_for_attrition(n: int, attrition_rate: float) -> dict[str, int | float]:
    return {
        "n": n,
        "attrition_rate": attrition_rate,
        "n_adjusted": core.adjust_for_attrition(n, attrition_rate),
    }


@server.tool(
    description="Largest-remainder integer allocation of a total sample across strata (e.g. sites, scanners, age bands)."
)
def allocate_strata(total: int, proportions: dict[str, float]) -> core.StrataAllocation:
    return _call(core.allocate_strata, total, proportions)
