"""Pure, deterministic biostatistics routines.

Every function here is side-effect free and returns plain Python / pydantic objects.
Formulas and references:

* One-sample proportion vs. performance goal (normal approximation):
  Chow, Shao & Wang, *Sample Size Calculations in Clinical Research*, §4.
* Exact binomial design: enumerates the smallest n with a critical value c such that
  P(X ≥ c | p0) ≤ α and P(X ≥ c | p1) ≥ 1 − β.
* Buderer NM. *Acad Emerg Med* 1996;3:895–900 — sensitivity/specificity sample size
  given prevalence and a target confidence-interval half-width.
* Wilson score and Clopper–Pearson intervals for a binomial proportion.
* Two independent proportions (superiority / non-inferiority): Fleiss / Chow et al.
* Paired proportions (McNemar): Connor RJ. *Biometrics* 1987;43:207–211.
* AUC variance: Hanley JA, McNeil BJ. *Radiology* 1982;143:29–36.
* MRMC power: Hillis SL, Obuchowski NA, Berbaum KS. *Stat Med* 2011;30:3083–3104
  (Obuchowski–Rockette model with Hillis denominator degrees of freedom).

The MRMC implementation follows the published formulas but has not been cross-checked
against RJafroc / iMRMC output inside this repository; see tests for the internal
consistency checks that *are* enforced, and validate against those packages before
relying on the numbers in a regulatory submission.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, Field
from scipy import stats

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────


def _z(prob: float) -> float:
    """Standard-normal quantile."""
    return float(stats.norm.ppf(prob))


def _check_prob(name: str, value: float, *, open_interval: bool = True) -> None:
    lo_ok = value > 0 if open_interval else value >= 0
    hi_ok = value < 1 if open_interval else value <= 1
    if not (lo_ok and hi_ok):
        rng = "(0, 1)" if open_interval else "[0, 1]"
        raise ValueError(f"{name} must lie in {rng}; got {value!r}")


def alpha_for_test(alpha: float, one_sided: bool) -> float:
    """Return the per-tail alpha used in z-quantiles.

    Regulatory convention for performance-goal studies is a one-sided test at 0.025,
    which is numerically identical to a two-sided 0.05 test for a single comparison.
    """
    return alpha if one_sided else alpha / 2


def adjust_for_attrition(n: int, attrition_rate: float) -> int:
    """Inflate a sample size for expected drop-out / unevaluable cases."""
    _check_prob("attrition_rate", attrition_rate, open_interval=False)
    if attrition_rate >= 1:
        raise ValueError("attrition_rate must be < 1")
    return math.ceil(n / (1.0 - attrition_rate))


# ─────────────────────────────────────────────────────────────────────────────
# Confidence intervals
# ─────────────────────────────────────────────────────────────────────────────


class ProportionCI(BaseModel):
    successes: int
    trials: int
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    method: Literal["wilson", "clopper_pearson", "wald"]


def proportion_ci(
    successes: int,
    trials: int,
    *,
    alpha: float = 0.05,
    method: Literal["wilson", "clopper_pearson", "wald"] = "wilson",
) -> ProportionCI:
    """Two-sided (1 − alpha) confidence interval for a binomial proportion."""
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 <= successes <= trials:
        raise ValueError("successes must be between 0 and trials")
    _check_prob("alpha", alpha)
    p_hat = successes / trials
    z = _z(1 - alpha / 2)

    if method == "wilson":
        denom = 1 + z**2 / trials
        centre = (p_hat + z**2 / (2 * trials)) / denom
        half = z * math.sqrt(p_hat * (1 - p_hat) / trials + z**2 / (4 * trials**2)) / denom
        lower, upper = centre - half, centre + half
    elif method == "clopper_pearson":
        lower = (
            0.0
            if successes == 0
            else float(stats.beta.ppf(alpha / 2, successes, trials - successes + 1))
        )
        upper = (
            1.0
            if successes == trials
            else float(stats.beta.ppf(1 - alpha / 2, successes + 1, trials - successes))
        )
    elif method == "wald":
        half = z * math.sqrt(p_hat * (1 - p_hat) / trials)
        lower, upper = p_hat - half, p_hat + half
    else:  # pragma: no cover - guarded by Literal
        raise ValueError(f"unknown method {method}")

    return ProportionCI(
        successes=successes,
        trials=trials,
        estimate=p_hat,
        lower=max(0.0, lower),
        upper=min(1.0, upper),
        confidence_level=1 - alpha,
        method=method,
    )


class DiagnosticAccuracy(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int
    sensitivity: ProportionCI
    specificity: ProportionCI
    ppv: ProportionCI
    npv: ProportionCI
    prevalence_in_sample: float
    accuracy: float
    youden_index: float


def diagnostic_accuracy_from_counts(
    tp: int, fp: int, fn: int, tn: int, *, alpha: float = 0.05
) -> DiagnosticAccuracy:
    """Sensitivity / specificity / PPV / NPV with Wilson intervals from a 2×2 table."""
    for name, v in (("tp", tp), ("fp", fp), ("fn", fn), ("tn", tn)):
        if v < 0:
            raise ValueError(f"{name} must be non-negative")
    n = tp + fp + fn + tn
    if n == 0:
        raise ValueError("2×2 table is empty")
    sens = proportion_ci(tp, max(tp + fn, 1), alpha=alpha)
    spec = proportion_ci(tn, max(tn + fp, 1), alpha=alpha)
    ppv = proportion_ci(tp, max(tp + fp, 1), alpha=alpha)
    npv = proportion_ci(tn, max(tn + fn, 1), alpha=alpha)
    return DiagnosticAccuracy(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        sensitivity=sens,
        specificity=spec,
        ppv=ppv,
        npv=npv,
        prevalence_in_sample=(tp + fn) / n,
        accuracy=(tp + tn) / n,
        youden_index=sens.estimate + spec.estimate - 1,
    )


# ─────────────────────────────────────────────────────────────────────────────
# One-sample proportion versus a performance goal
# ─────────────────────────────────────────────────────────────────────────────


class OneSampleProportionResult(BaseModel):
    """Sample size for H0: p ≤ p0 vs H1: p > p0 (or the mirrored lower-tail test)."""

    n: int = Field(description="Required number of evaluable cases")
    p0: float = Field(description="Performance goal / null proportion")
    p1: float = Field(description="Expected (alternative) proportion")
    alpha: float
    one_sided: bool
    target_power: float
    achieved_power: float
    method: Literal["normal", "exact_binomial"]
    critical_successes: int | None = Field(
        default=None,
        description="Exact design only: minimum successes required to reject H0",
    )
    achieved_alpha: float | None = Field(
        default=None, description="Exact design only: actual type-I error at p0"
    )
    direction: Literal["greater", "less"]
    notes: list[str] = Field(default_factory=list)


def _normal_n_one_sample(p0: float, p1: float, alpha_tail: float, power: float) -> float:
    z_a = _z(1 - alpha_tail)
    z_b = _z(power)
    num = z_a * math.sqrt(p0 * (1 - p0)) + z_b * math.sqrt(p1 * (1 - p1))
    return (num / (p1 - p0)) ** 2


def _exact_design(
    p0: float, p1: float, alpha_tail: float, power: float, n_start: int
) -> tuple[int, int, float, float]:
    """Smallest n (≥ n_start) with a critical value c achieving size ≤ α and power ≥ 1−β.

    Returns (n, c, achieved_alpha, achieved_power). Upper-tail test: reject if X ≥ c.
    """
    n = max(1, n_start)
    for _ in range(100_000):
        # smallest c with P(X >= c | p0) <= alpha  ⇔  sf(c-1) <= alpha
        # binom.isf gives the smallest k with sf(k) <= alpha, i.e. P(X > k) <= alpha  ⇒ c = k + 1
        k = int(stats.binom.isf(alpha_tail, n, p0))
        c = k + 1
        size = float(stats.binom.sf(c - 1, n, p0))
        pw = float(stats.binom.sf(c - 1, n, p1))
        if size <= alpha_tail + 1e-12 and pw >= power - 1e-12:
            return n, c, size, pw
        n += 1
    raise RuntimeError("exact design search did not converge")


def one_sample_proportion_sample_size(
    p0: float,
    p1: float,
    *,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    method: Literal["normal", "exact_binomial"] = "exact_binomial",
) -> OneSampleProportionResult:
    """Cases needed to show a proportion exceeds (or falls below) a performance goal.

    If ``p1 < p0`` the test is a lower-tail test (e.g. a false-positive rate that must be
    *below* a goal); it is solved by mirroring both proportions.
    """
    _check_prob("p0", p0)
    _check_prob("p1", p1)
    _check_prob("alpha", alpha)
    _check_prob("power", power)
    if p0 == p1:
        raise ValueError("p0 and p1 must differ")
    direction: Literal["greater", "less"] = "greater" if p1 > p0 else "less"
    q0, q1 = (p0, p1) if direction == "greater" else (1 - p0, 1 - p1)
    a_tail = alpha_for_test(alpha, one_sided)
    notes: list[str] = []

    n_norm = _normal_n_one_sample(q0, q1, a_tail, power)
    if method == "normal":
        n = math.ceil(n_norm)
        # achieved power under the normal approximation
        se0 = math.sqrt(q0 * (1 - q0) / n)
        se1 = math.sqrt(q1 * (1 - q1) / n)
        crit = q0 + _z(1 - a_tail) * se0
        achieved = float(stats.norm.sf((crit - q1) / se1))
        return OneSampleProportionResult(
            n=n,
            p0=p0,
            p1=p1,
            alpha=alpha,
            one_sided=one_sided,
            target_power=power,
            achieved_power=achieved,
            method="normal",
            direction=direction,
            notes=notes,
        )

    n, c, size, pw = _exact_design(q0, q1, a_tail, power, int(max(1, math.floor(n_norm * 0.8))))
    if direction == "less":
        notes.append(
            "Lower-tail test solved on the complementary proportion; critical_successes refers to "
            "the complementary event (e.g. true negatives for a specificity goal)."
        )
    notes.append(
        "Exact binomial power is non-monotone in n (saw-tooth); n is the smallest value "
        "satisfying both the size and power constraints."
    )
    return OneSampleProportionResult(
        n=n,
        p0=p0,
        p1=p1,
        alpha=alpha,
        one_sided=one_sided,
        target_power=power,
        achieved_power=pw,
        method="exact_binomial",
        critical_successes=c,
        achieved_alpha=size,
        direction=direction,
        notes=notes,
    )


class StandaloneSampleSize(BaseModel):
    """Positive / negative case requirements for a standalone performance study."""

    sensitivity: OneSampleProportionResult | None
    specificity: OneSampleProportionResult | None
    n_positive: int
    n_negative: int
    n_total: int
    n_positive_with_attrition: int
    n_negative_with_attrition: int
    n_total_with_attrition: int
    attrition_rate: float
    prevalence_assumed: float | None = Field(
        default=None,
        description="If given, the total enrolment implied by sampling at this prevalence",
    )
    n_total_at_prevalence: int | None = None
    notes: list[str] = Field(default_factory=list)


def standalone_sample_size(
    *,
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
) -> StandaloneSampleSize:
    """Co-primary sensitivity & specificity performance-goal design (FDA CADe/CADx style).

    Each endpoint is tested separately against its own goal; no multiplicity adjustment is
    applied because both must succeed (intersection-union test keeps type-I error ≤ α).
    """
    if expected_sensitivity is None and expected_specificity is None:
        raise ValueError("at least one of sensitivity or specificity must be specified")
    notes: list[str] = [
        "Co-primary endpoints (sensitivity AND specificity) are each tested at the full alpha; "
        "the intersection-union test controls the family-wise error without adjustment."
    ]
    sens_res = spec_res = None
    n_pos = n_neg = 0
    if expected_sensitivity is not None:
        if sensitivity_goal is None:
            raise ValueError("sensitivity_goal is required with expected_sensitivity")
        sens_res = one_sample_proportion_sample_size(
            sensitivity_goal,
            expected_sensitivity,
            alpha=alpha,
            power=power,
            one_sided=one_sided,
            method=method,
        )
        n_pos = sens_res.n
    if expected_specificity is not None:
        if specificity_goal is None:
            raise ValueError("specificity_goal is required with expected_specificity")
        spec_res = one_sample_proportion_sample_size(
            specificity_goal,
            expected_specificity,
            alpha=alpha,
            power=power,
            one_sided=one_sided,
            method=method,
        )
        n_neg = spec_res.n

    n_pos_att = adjust_for_attrition(n_pos, attrition_rate) if n_pos else 0
    n_neg_att = adjust_for_attrition(n_neg, attrition_rate) if n_neg else 0

    n_total_prev = None
    if prevalence is not None:
        _check_prob("prevalence", prevalence)
        from_pos = n_pos_att / prevalence if n_pos_att else 0
        from_neg = n_neg_att / (1 - prevalence) if n_neg_att else 0
        n_total_prev = math.ceil(max(from_pos, from_neg))
        notes.append(
            "n_total_at_prevalence is the consecutive-enrolment size needed so that BOTH the "
            "positive and negative targets are met at the assumed prevalence; enriched "
            "(case-control) sampling can use n_positive + n_negative directly."
        )

    return StandaloneSampleSize(
        sensitivity=sens_res,
        specificity=spec_res,
        n_positive=n_pos,
        n_negative=n_neg,
        n_total=n_pos + n_neg,
        n_positive_with_attrition=n_pos_att,
        n_negative_with_attrition=n_neg_att,
        n_total_with_attrition=n_pos_att + n_neg_att,
        attrition_rate=attrition_rate,
        prevalence_assumed=prevalence,
        n_total_at_prevalence=n_total_prev,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Buderer (1996): precision-based sensitivity / specificity sample size
# ─────────────────────────────────────────────────────────────────────────────


class BudererResult(BaseModel):
    n_positive: int
    n_negative: int
    n_total_from_sensitivity: int = Field(description="n_positive / prevalence")
    n_total_from_specificity: int = Field(description="n_negative / (1 − prevalence)")
    n_total_required: int = Field(description="max of the two totals")
    n_total_with_attrition: int
    confidence_level: float
    assumptions: dict[str, float]


def buderer_sample_size(
    *,
    expected_sensitivity: float,
    expected_specificity: float,
    prevalence: float,
    ci_halfwidth_sensitivity: float = 0.05,
    ci_halfwidth_specificity: float = 0.05,
    alpha: float = 0.05,
    attrition_rate: float = 0.10,
) -> BudererResult:
    """Sample size so that each of sensitivity and specificity has a CI of given half-width."""
    for name, v in (
        ("expected_sensitivity", expected_sensitivity),
        ("expected_specificity", expected_specificity),
        ("prevalence", prevalence),
        ("ci_halfwidth_sensitivity", ci_halfwidth_sensitivity),
        ("ci_halfwidth_specificity", ci_halfwidth_specificity),
        ("alpha", alpha),
    ):
        _check_prob(name, v)
    z = _z(1 - alpha / 2)
    n_pos = math.ceil(
        z**2 * expected_sensitivity * (1 - expected_sensitivity) / ci_halfwidth_sensitivity**2
    )
    n_neg = math.ceil(
        z**2 * expected_specificity * (1 - expected_specificity) / ci_halfwidth_specificity**2
    )
    tot_sens = math.ceil(n_pos / prevalence)
    tot_spec = math.ceil(n_neg / (1 - prevalence))
    total = max(tot_sens, tot_spec)
    return BudererResult(
        n_positive=n_pos,
        n_negative=n_neg,
        n_total_from_sensitivity=tot_sens,
        n_total_from_specificity=tot_spec,
        n_total_required=total,
        n_total_with_attrition=adjust_for_attrition(total, attrition_rate),
        confidence_level=1 - alpha,
        assumptions={
            "expected_sensitivity": expected_sensitivity,
            "expected_specificity": expected_specificity,
            "prevalence": prevalence,
            "ci_halfwidth_sensitivity": ci_halfwidth_sensitivity,
            "ci_halfwidth_specificity": ci_halfwidth_specificity,
            "attrition_rate": attrition_rate,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Two independent proportions
# ─────────────────────────────────────────────────────────────────────────────


class TwoProportionResult(BaseModel):
    n_test: int
    n_reference: int
    n_total: int
    n_total_with_attrition: int
    p_test: float
    p_reference: float
    hypothesis: Literal["superiority", "non_inferiority"]
    margin: float
    alpha: float
    one_sided: bool
    power: float
    allocation_ratio: float
    notes: list[str] = Field(default_factory=list)


def two_proportion_sample_size(
    *,
    p_test: float,
    p_reference: float,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    hypothesis: Literal["superiority", "non_inferiority"] = "superiority",
    margin: float = 0.0,
    allocation_ratio: float = 1.0,
    attrition_rate: float = 0.10,
) -> TwoProportionResult:
    """Independent-groups design (e.g. prospective RCT: AI-assisted arm vs. standard care).

    Non-inferiority: H0: p_test − p_ref ≤ −margin  vs  H1: p_test − p_ref > −margin.
    ``allocation_ratio`` = n_test / n_reference.
    """
    _check_prob("p_test", p_test)
    _check_prob("p_reference", p_reference)
    _check_prob("alpha", alpha)
    _check_prob("power", power)
    if allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be positive")
    k = allocation_ratio
    a_tail = alpha_for_test(alpha, one_sided)
    z_a, z_b = _z(1 - a_tail), _z(power)
    notes: list[str] = []

    if hypothesis == "superiority":
        if p_test == p_reference:
            raise ValueError("p_test and p_reference must differ for superiority")
        p_bar = (k * p_test + p_reference) / (1 + k)
        q_bar = 1 - p_bar
        num = z_a * math.sqrt(p_bar * q_bar * (1 + 1 / k)) + z_b * math.sqrt(
            p_test * (1 - p_test) + p_reference * (1 - p_reference) / k
        )
        n_test = math.ceil((num / (p_test - p_reference)) ** 2)
        n_ref = math.ceil(n_test / k)
        notes.append("Fleiss pooled-variance formula without continuity correction.")
    else:
        if margin <= 0:
            raise ValueError("non-inferiority margin must be positive")
        if p_test - p_reference + margin <= 0:
            raise ValueError("expected difference must exceed −margin for a feasible NI design")
        var = p_test * (1 - p_test) / k + p_reference * (1 - p_reference)
        n_ref = math.ceil((z_a + z_b) ** 2 * var / (p_test - p_reference + margin) ** 2)
        n_test = math.ceil(k * n_ref)
        notes.append("Chow–Shao–Wang non-inferiority formula for the difference in proportions.")

    total = n_test + n_ref
    return TwoProportionResult(
        n_test=n_test,
        n_reference=n_ref,
        n_total=total,
        n_total_with_attrition=adjust_for_attrition(total, attrition_rate),
        p_test=p_test,
        p_reference=p_reference,
        hypothesis=hypothesis,
        margin=margin,
        alpha=alpha,
        one_sided=one_sided,
        power=power,
        allocation_ratio=k,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Paired proportions (McNemar / Connor 1987)
# ─────────────────────────────────────────────────────────────────────────────


class PairedProportionResult(BaseModel):
    n_pairs: int = Field(description="Cases read under both conditions")
    n_pairs_with_attrition: int
    p_test: float
    p_reference: float
    difference: float
    discordant_proportion: float
    discordance_assumption: Literal["provided", "independence"]
    alpha: float
    one_sided: bool
    power: float
    hypothesis: Literal["superiority", "non_inferiority"]
    margin: float
    notes: list[str] = Field(default_factory=list)


def paired_proportion_sample_size(
    *,
    p_test: float,
    p_reference: float,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    discordant_proportion: float | None = None,
    hypothesis: Literal["superiority", "non_inferiority"] = "superiority",
    margin: float = 0.0,
    attrition_rate: float = 0.10,
) -> PairedProportionResult:
    """Paired design where every case is evaluated under both conditions.

    Typical uses: standalone AI vs. the same radiologists on the same cases; sensitivity
    with vs. without AI in a single-reader crossover. Uses Connor's (1987) formula
    n = [z_α √ψ + z_β √(ψ − δ²)]² / δ², with δ = p_test − p_reference (+ margin for NI)
    and ψ the proportion of discordant pairs. When ψ is unknown it is set under the
    independence assumption ψ = p_t(1−p_r) + p_r(1−p_t), which is conservative when the
    two conditions are positively correlated (the usual situation).
    """
    _check_prob("p_test", p_test)
    _check_prob("p_reference", p_reference)
    _check_prob("alpha", alpha)
    _check_prob("power", power)
    delta = p_test - p_reference
    if hypothesis == "non_inferiority":
        if margin <= 0:
            raise ValueError("non-inferiority margin must be positive")
        delta = delta + margin
    if delta <= 0:
        raise ValueError("expected difference (plus NI margin) must be positive")

    if discordant_proportion is None:
        psi = p_test * (1 - p_reference) + p_reference * (1 - p_test)
        assumption: Literal["provided", "independence"] = "independence"
    else:
        _check_prob("discordant_proportion", discordant_proportion)
        psi = discordant_proportion
        assumption = "provided"
    if psi < abs(p_test - p_reference):
        raise ValueError("discordant_proportion cannot be smaller than |p_test − p_reference|")
    if psi - delta**2 < 0:
        raise ValueError(
            "inconsistent inputs: discordant proportion too small for the stated difference"
        )

    a_tail = alpha_for_test(alpha, one_sided)
    z_a, z_b = _z(1 - a_tail), _z(power)
    n = math.ceil(((z_a * math.sqrt(psi) + z_b * math.sqrt(psi - delta**2)) / delta) ** 2)
    notes = ["Connor (1987) McNemar sample size; n counts cases (pairs), not readings."]
    if assumption == "independence":
        notes.append(
            "Discordant proportion set under independence; supply a pilot-based value for a "
            "tighter estimate."
        )
    return PairedProportionResult(
        n_pairs=n,
        n_pairs_with_attrition=adjust_for_attrition(n, attrition_rate),
        p_test=p_test,
        p_reference=p_reference,
        difference=p_test - p_reference,
        discordant_proportion=psi,
        discordance_assumption=assumption,
        alpha=alpha,
        one_sided=one_sided,
        power=power,
        hypothesis=hypothesis,
        margin=margin,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AUC (Hanley–McNeil 1982)
# ─────────────────────────────────────────────────────────────────────────────


def hanley_mcneil_variance(auc: float, n_pos: int, n_neg: int) -> float:
    """Variance of an empirical AUC estimate (binormal-free approximation)."""
    _check_prob("auc", auc)
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    return (auc * (1 - auc) + (n_pos - 1) * (q1 - auc**2) + (n_neg - 1) * (q2 - auc**2)) / (
        n_pos * n_neg
    )


class AUCSampleSizeResult(BaseModel):
    n_positive: int
    n_negative: int
    n_total: int
    n_total_with_attrition: int
    expected_auc: float
    auc_goal: float | None
    ci_halfwidth: float | None
    alpha: float
    one_sided: bool | None
    power: float | None
    negative_to_positive_ratio: float
    standard_error_at_n: float
    mode: Literal["precision", "performance_goal"]
    notes: list[str] = Field(default_factory=list)


def auc_sample_size(
    *,
    expected_auc: float,
    auc_goal: float | None = None,
    ci_halfwidth: float | None = None,
    alpha: float = 0.025,
    power: float = 0.80,
    one_sided: bool = True,
    negative_to_positive_ratio: float = 1.0,
    attrition_rate: float = 0.10,
) -> AUCSampleSizeResult:
    """Cases needed for an AUROC endpoint.

    * ``ci_halfwidth`` → precision mode: smallest n_pos such that z·SE(AUC) ≤ half-width.
    * ``auc_goal``     → performance-goal mode: H0: AUC ≤ goal, solved with the normal
      approximation using Hanley–McNeil variances under H0 and H1.
    """
    _check_prob("expected_auc", expected_auc)
    _check_prob("alpha", alpha)
    if negative_to_positive_ratio <= 0:
        raise ValueError("negative_to_positive_ratio must be positive")
    if (auc_goal is None) == (ci_halfwidth is None):
        raise ValueError("specify exactly one of auc_goal or ci_halfwidth")
    r = negative_to_positive_ratio
    notes: list[str] = ["Hanley & McNeil (1982) variance approximation for the empirical AUC."]

    def se(a: float, n_pos: int) -> float:
        n_neg = max(1, math.ceil(n_pos * r))
        return math.sqrt(hanley_mcneil_variance(a, n_pos, n_neg))

    n_pos = 2
    if ci_halfwidth is not None:
        _check_prob("ci_halfwidth", ci_halfwidth)
        z = _z(1 - alpha / 2)
        while z * se(expected_auc, n_pos) > ci_halfwidth and n_pos < 1_000_000:
            n_pos += 1
        mode: Literal["precision", "performance_goal"] = "precision"
        notes.append("Two-sided interval; alpha interpreted as 1 − confidence level.")
        pwr: float | None = None
        one_sided_out: bool | None = None
    else:
        assert auc_goal is not None
        _check_prob("auc_goal", auc_goal)
        _check_prob("power", power)
        if expected_auc <= auc_goal:
            raise ValueError("expected_auc must exceed auc_goal")
        a_tail = alpha_for_test(alpha, one_sided)
        z_a, z_b = _z(1 - a_tail), _z(power)
        while (z_a * se(auc_goal, n_pos) + z_b * se(expected_auc, n_pos)) > (
            expected_auc - auc_goal
        ) and n_pos < 1_000_000:
            n_pos += 1
        mode = "performance_goal"
        pwr = power
        one_sided_out = one_sided

    n_neg = math.ceil(n_pos * r)
    total = n_pos + n_neg
    return AUCSampleSizeResult(
        n_positive=n_pos,
        n_negative=n_neg,
        n_total=total,
        n_total_with_attrition=adjust_for_attrition(total, attrition_rate),
        expected_auc=expected_auc,
        auc_goal=auc_goal,
        ci_halfwidth=ci_halfwidth,
        alpha=alpha,
        one_sided=one_sided_out,
        power=pwr,
        negative_to_positive_ratio=r,
        standard_error_at_n=se(expected_auc, n_pos),
        mode=mode,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MRMC — Obuchowski–Rockette model, Hillis (2011) power
# ─────────────────────────────────────────────────────────────────────────────


class ORVarianceComponents(BaseModel):
    """OR-model variance components estimated from a pilot study of ``pilot_cases`` cases.

    All quantities are on the scale of the reader-level figure of merit (e.g. AUC).
    """

    var_treatment_reader: float = Field(ge=0, description="σ²_TR — treatment × reader interaction")
    var_error: float = Field(
        gt=0, description="σ²_ε — within reader/treatment error (case sampling)"
    )
    cov1: float = Field(description="Cov1 — same reader, different treatments")
    cov2: float = Field(description="Cov2 — different readers, same treatment")
    cov3: float = Field(description="Cov3 — different readers, different treatments")
    pilot_cases: int = Field(gt=0, description="Number of cases the components were estimated from")

    def scaled_to(self, cases: int) -> ORVarianceComponents:
        """Rescale case-dependent components to a new case count (∝ 1/cases)."""
        f = self.pilot_cases / cases
        return ORVarianceComponents(
            var_treatment_reader=self.var_treatment_reader,
            var_error=self.var_error * f,
            cov1=self.cov1 * f,
            cov2=self.cov2 * f,
            cov3=self.cov3 * f,
            pilot_cases=cases,
        )


class MRMCPowerResult(BaseModel):
    readers: int
    cases: int
    modalities: int
    effect_size: float = Field(description="Difference in the figure of merit between modalities")
    alpha: float
    power: float
    noncentrality: float
    ddf_hillis: float
    f_critical: float
    denominator_variance: float
    components_at_cases: ORVarianceComponents
    notes: list[str] = Field(default_factory=list)


def mrmc_power(
    *,
    readers: int,
    cases: int,
    effect_size: float,
    components: ORVarianceComponents,
    alpha: float = 0.05,
    modalities: int = 2,
) -> MRMCPowerResult:
    """Power of the OR F-test for a fully-crossed MRMC study (Hillis et al. 2011).

    ``effect_size`` is the expected difference between the two modality means of the
    figure of merit (e.g. AUC with AI minus AUC without AI). ``alpha`` is two-sided in the
    sense of the F-test (a two-modality F-test at 0.05 ≙ two-sided t-test at 0.05).
    """
    if readers < 2:
        raise ValueError("readers must be ≥ 2")
    if cases < 2:
        raise ValueError("cases must be ≥ 2")
    if modalities != 2:
        raise ValueError("only two-modality designs are supported (effect_size is a difference)")
    _check_prob("alpha", alpha)
    t, r = modalities, readers
    vc = components.scaled_to(cases)
    ms_tr_expected = vc.var_treatment_reader + vc.var_error - vc.cov1 - vc.cov2 + vc.cov3
    if ms_tr_expected <= 0:
        raise ValueError(
            "inconsistent variance components: σ²_TR + σ²_ε − Cov1 − Cov2 + Cov3 must be > 0"
        )
    extra = max(r * (vc.cov2 - vc.cov3), 0.0)
    denom = ms_tr_expected + extra
    sum_tau_sq = (effect_size**2) / 2.0  # two modalities with effects ±Δ/2
    lam = r * sum_tau_sq / denom
    ddf_h = denom**2 / (ms_tr_expected**2 / ((t - 1) * (r - 1)))
    ndf = t - 1
    f_crit = float(stats.f.ppf(1 - alpha, ndf, ddf_h))
    # scipy's non-central F is undefined at λ = 0; fall back to the central F there.
    power = (
        float(stats.f.sf(f_crit, ndf, ddf_h))
        if lam < 1e-12
        else float(stats.ncf.sf(f_crit, ndf, ddf_h, lam))
    )
    notes = [
        "Obuchowski–Rockette F-test with Hillis denominator degrees of freedom; case-dependent "
        "components rescaled by pilot_cases/cases.",
        "Validate against RJafroc::SsPowerGivenJK or iMRMC before regulatory use.",
    ]
    return MRMCPowerResult(
        readers=readers,
        cases=cases,
        modalities=t,
        effect_size=effect_size,
        alpha=alpha,
        power=power,
        noncentrality=lam,
        ddf_hillis=ddf_h,
        f_critical=f_crit,
        denominator_variance=denom,
        components_at_cases=vc,
        notes=notes,
    )


class MRMCSampleSizeResult(BaseModel):
    target_power: float
    readers: int
    cases_required: int
    cases_with_attrition: int
    achieved_power: float
    effect_size: float
    alpha: float
    max_power_at_limit: float | None = Field(
        default=None,
        description="If the target is unattainable within max_cases, the power at max_cases",
    )
    notes: list[str] = Field(default_factory=list)


def mrmc_cases_needed(
    *,
    readers: int,
    effect_size: float,
    components: ORVarianceComponents,
    alpha: float = 0.05,
    power: float = 0.80,
    attrition_rate: float = 0.10,
    max_cases: int = 5000,
) -> MRMCSampleSizeResult:
    """Smallest case count reaching the target power for a fixed reader panel."""
    _check_prob("power", power)
    lo, hi = 2, max_cases
    p_hi = mrmc_power(
        readers=readers, cases=hi, effect_size=effect_size, components=components, alpha=alpha
    ).power
    if p_hi < power:
        return MRMCSampleSizeResult(
            target_power=power,
            readers=readers,
            cases_required=hi,
            cases_with_attrition=adjust_for_attrition(hi, attrition_rate),
            achieved_power=p_hi,
            effect_size=effect_size,
            alpha=alpha,
            max_power_at_limit=p_hi,
            notes=[
                "Target power is unattainable by adding cases alone: reader-related variance "
                "(σ²_TR) bounds the achievable power. Increase the number of readers."
            ],
        )
    # power is monotone non-decreasing in cases → bisection
    while lo < hi:
        mid = (lo + hi) // 2
        p_mid = mrmc_power(
            readers=readers, cases=mid, effect_size=effect_size, components=components, alpha=alpha
        ).power
        if p_mid >= power:
            hi = mid
        else:
            lo = mid + 1
    achieved = mrmc_power(
        readers=readers, cases=lo, effect_size=effect_size, components=components, alpha=alpha
    ).power
    return MRMCSampleSizeResult(
        target_power=power,
        readers=readers,
        cases_required=lo,
        cases_with_attrition=adjust_for_attrition(lo, attrition_rate),
        achieved_power=achieved,
        effect_size=effect_size,
        alpha=alpha,
        notes=["Cases are total cases (positives + negatives) in the fully-crossed design."],
    )


class MRMCReaderCaseGrid(BaseModel):
    effect_size: float
    alpha: float
    target_power: float
    grid: list[dict[str, float | int | None]] = Field(
        description="For each reader count, the cases required (None if unattainable)"
    )


def mrmc_reader_case_grid(
    *,
    effect_size: float,
    components: ORVarianceComponents,
    reader_counts: list[int],
    alpha: float = 0.05,
    power: float = 0.80,
    max_cases: int = 5000,
) -> MRMCReaderCaseGrid:
    """Trade-off table: readers vs. cases needed, useful for protocol justification."""
    rows: list[dict[str, float | int | None]] = []
    for r in reader_counts:
        res = mrmc_cases_needed(
            readers=r,
            effect_size=effect_size,
            components=components,
            alpha=alpha,
            power=power,
            max_cases=max_cases,
        )
        rows.append(
            {
                "readers": r,
                "cases": None if res.max_power_at_limit is not None else res.cases_required,
                "achieved_power": res.achieved_power,
            }
        )
    return MRMCReaderCaseGrid(effect_size=effect_size, alpha=alpha, target_power=power, grid=rows)


# ─────────────────────────────────────────────────────────────────────────────
# Allocation helpers
# ─────────────────────────────────────────────────────────────────────────────


class StrataAllocation(BaseModel):
    total: int
    allocation: dict[str, int]
    proportions: dict[str, float]


def allocate_strata(total: int, proportions: dict[str, float]) -> StrataAllocation:
    """Largest-remainder (Hamilton) integer allocation of ``total`` across strata."""
    if total <= 0:
        raise ValueError("total must be positive")
    if not proportions:
        raise ValueError("proportions must not be empty")
    s = sum(proportions.values())
    if s <= 0:
        raise ValueError("proportions must sum to a positive number")
    norm = {k: v / s for k, v in proportions.items()}
    raw = {k: total * v for k, v in norm.items()}
    floors = {k: math.floor(v) for k, v in raw.items()}
    remainder = total - sum(floors.values())
    order = sorted(raw, key=lambda k: raw[k] - floors[k], reverse=True)
    for k in order[:remainder]:
        floors[k] += 1
    return StrataAllocation(total=total, allocation=floors, proportions=norm)
