import math

import pytest

from mcp_biostat_calc import core

# ── confidence intervals ─────────────────────────────────────────────────────


def test_wilson_matches_known_value():
    # 85/100 → Wilson 95% CI ≈ (0.767, 0.907)
    ci = core.proportion_ci(85, 100, method="wilson")
    assert ci.lower == pytest.approx(0.7669, abs=2e-3)
    assert ci.upper == pytest.approx(0.9068, abs=2e-3)


def test_clopper_pearson_known_value():
    # 85/100 → exact 95% CI ≈ (0.7647, 0.9135)
    ci = core.proportion_ci(85, 100, method="clopper_pearson")
    assert ci.lower == pytest.approx(0.7647, abs=1e-3)
    assert ci.upper == pytest.approx(0.9135, abs=1e-3)


def test_ci_edge_cases_are_bounded():
    assert core.proportion_ci(0, 10, method="clopper_pearson").lower == 0.0
    assert core.proportion_ci(10, 10, method="clopper_pearson").upper == 1.0
    wald = core.proportion_ci(10, 10, method="wald")
    assert wald.lower <= wald.upper <= 1.0


def test_diagnostic_accuracy_from_counts():
    d = core.diagnostic_accuracy_from_counts(tp=90, fp=10, fn=10, tn=90)
    assert d.sensitivity.estimate == pytest.approx(0.9)
    assert d.specificity.estimate == pytest.approx(0.9)
    assert d.ppv.estimate == pytest.approx(0.9)
    assert d.youden_index == pytest.approx(0.8)
    assert d.prevalence_in_sample == pytest.approx(0.5)


# ── one-sample proportion ────────────────────────────────────────────────────


def test_normal_one_sample_matches_closed_form():
    # p0=0.30, p1=0.50, one-sided alpha 0.05, power 0.80:
    # n = [1.6449·√(0.21) + 0.8416·√(0.25)]² / 0.2² = 34.5 → 35
    res = core.one_sample_proportion_sample_size(
        0.30, 0.50, alpha=0.05, power=0.80, one_sided=True, method="normal"
    )
    z_a, z_b = 1.6448536, 0.8416212
    expected = math.ceil(((z_a * math.sqrt(0.21) + z_b * math.sqrt(0.25)) / 0.2) ** 2)
    assert res.n == expected == 35
    assert res.achieved_power >= 0.79


def test_exact_design_controls_size_and_power():
    res = core.one_sample_proportion_sample_size(
        0.82, 0.92, alpha=0.025, power=0.80, method="exact_binomial"
    )
    assert res.achieved_alpha <= 0.025
    assert res.achieved_power >= 0.80
    assert res.critical_successes is not None and res.critical_successes <= res.n
    # exact design should be in the same ball-park as the normal approximation
    normal = core.one_sample_proportion_sample_size(
        0.82, 0.92, alpha=0.025, power=0.80, method="normal"
    )
    assert abs(res.n - normal.n) / normal.n < 0.35


def test_lower_tail_mirrors_upper_tail():
    up = core.one_sample_proportion_sample_size(0.80, 0.90, method="exact_binomial")
    down = core.one_sample_proportion_sample_size(0.20, 0.10, method="exact_binomial")
    assert up.n == down.n
    assert down.direction == "less"


def test_one_sample_rejects_bad_inputs():
    with pytest.raises(ValueError):
        core.one_sample_proportion_sample_size(0.5, 0.5)
    with pytest.raises(ValueError):
        core.one_sample_proportion_sample_size(1.2, 0.5)


def test_standalone_combines_sens_spec_and_prevalence():
    res = core.standalone_sample_size(
        expected_sensitivity=0.92,
        sensitivity_goal=0.82,
        expected_specificity=0.90,
        specificity_goal=0.80,
        alpha=0.025,
        power=0.80,
        attrition_rate=0.10,
        prevalence=0.20,
    )
    assert res.n_positive > 0 and res.n_negative > 0
    assert res.n_total == res.n_positive + res.n_negative
    assert res.n_positive_with_attrition == math.ceil(res.n_positive / 0.9)
    # at 20 % prevalence the positives drive the consecutive-enrolment total
    assert res.n_total_at_prevalence >= res.n_positive_with_attrition / 0.20 - 1


def test_standalone_requires_goal():
    with pytest.raises(ValueError):
        core.standalone_sample_size(expected_sensitivity=0.9)


# ── Buderer ──────────────────────────────────────────────────────────────────


def test_buderer_reproduces_paper_style_numbers():
    # sens 0.90, spec 0.85, prevalence 0.10, half-width 0.05, 95 % → n_pos=139, n_neg=196
    res = core.buderer_sample_size(
        expected_sensitivity=0.90,
        expected_specificity=0.85,
        prevalence=0.10,
        ci_halfwidth_sensitivity=0.05,
        ci_halfwidth_specificity=0.05,
        alpha=0.05,
        attrition_rate=0.0,
    )
    assert res.n_positive == 139
    assert res.n_negative == 196
    assert res.n_total_from_sensitivity == 1390
    assert res.n_total_from_specificity == math.ceil(196 / 0.9)
    assert res.n_total_required == 1390


# ── two independent proportions ──────────────────────────────────────────────


def test_two_proportion_superiority_textbook():
    # p1=0.65 vs p2=0.85, two-sided 0.05, power 0.80 (Fleiss, no CC):
    # [1.96·√(2·0.75·0.25) + 0.8416·√(0.1275+0.2275)]² / 0.2² = 72.4 → 73 per group
    res = core.two_proportion_sample_size(
        p_test=0.85, p_reference=0.65, alpha=0.05, one_sided=False, power=0.80, attrition_rate=0.0
    )
    assert res.n_test == 73
    assert res.n_test == res.n_reference


def test_two_proportion_non_inferiority():
    # Chow et al. NI example: p_test=0.85, p_ref=0.65? use symmetric: pT=pR=0.85, margin 0.10, one-sided 0.025, power 0.8 → 156/group
    res = core.two_proportion_sample_size(
        p_test=0.85,
        p_reference=0.85,
        hypothesis="non_inferiority",
        margin=0.10,
        alpha=0.025,
        power=0.80,
        attrition_rate=0.0,
    )
    assert 198 <= res.n_test <= 202  # (1.96+0.8416)^2 * 2*0.1275 / 0.01 = 200.2


def test_two_proportion_allocation_ratio():
    res = core.two_proportion_sample_size(
        p_test=0.85, p_reference=0.65, allocation_ratio=2.0, attrition_rate=0.0
    )
    assert res.n_test == pytest.approx(2 * res.n_reference, abs=2)


# ── paired proportions ───────────────────────────────────────────────────────


def test_paired_connor_formula_known_value():
    # ψ=0.20, δ=0.10, one-sided 0.025, power 0.8:
    # [1.96·√0.20 + 0.8416·√(0.20−0.01)]² / 0.01 = 154.6 → 155
    res = core.paired_proportion_sample_size(
        p_test=0.90,
        p_reference=0.80,
        discordant_proportion=0.20,
        alpha=0.025,
        power=0.80,
        attrition_rate=0.0,
    )
    assert res.n_pairs == 155


def test_paired_independence_assumption_is_conservative():
    with_pilot = core.paired_proportion_sample_size(
        p_test=0.90, p_reference=0.80, discordant_proportion=0.14
    )
    independent = core.paired_proportion_sample_size(p_test=0.90, p_reference=0.80)
    assert independent.discordance_assumption == "independence"
    assert independent.n_pairs >= with_pilot.n_pairs


def test_paired_rejects_inconsistent_discordance():
    with pytest.raises(ValueError):
        core.paired_proportion_sample_size(
            p_test=0.90, p_reference=0.80, discordant_proportion=0.05
        )


# ── AUC ──────────────────────────────────────────────────────────────────────


def test_hanley_mcneil_variance_known_value():
    # AUC 0.85, 50 pos / 50 neg → SE ≈ 0.040 (Hanley & McNeil table region)
    se = math.sqrt(core.hanley_mcneil_variance(0.85, 50, 50))
    assert se == pytest.approx(0.0397, abs=0.004)


def test_auc_precision_mode_shrinks_with_wider_interval():
    tight = core.auc_sample_size(expected_auc=0.90, ci_halfwidth=0.03, alpha=0.05)
    loose = core.auc_sample_size(expected_auc=0.90, ci_halfwidth=0.06, alpha=0.05)
    assert tight.n_positive > loose.n_positive
    assert tight.mode == "precision"


def test_auc_goal_mode():
    res = core.auc_sample_size(
        expected_auc=0.90, auc_goal=0.80, alpha=0.025, power=0.80, negative_to_positive_ratio=2.0
    )
    assert res.mode == "performance_goal"
    assert res.n_negative == math.ceil(2 * res.n_positive)
    assert 40 <= res.n_positive <= 120


def test_auc_requires_exactly_one_mode():
    with pytest.raises(ValueError):
        core.auc_sample_size(expected_auc=0.9)
    with pytest.raises(ValueError):
        core.auc_sample_size(expected_auc=0.9, auc_goal=0.8, ci_halfwidth=0.05)


# ── MRMC ─────────────────────────────────────────────────────────────────────

PILOT = core.ORVarianceComponents(
    var_treatment_reader=0.0002,
    var_error=0.0015,
    cov1=0.0006,
    cov2=0.0005,
    cov3=0.0003,
    pilot_cases=100,
)


def test_mrmc_power_is_alpha_under_null():
    res = core.mrmc_power(readers=8, cases=200, effect_size=0.0, components=PILOT, alpha=0.05)
    assert res.power == pytest.approx(0.05, abs=1e-6)


def test_mrmc_power_continuous_near_null():
    tiny = core.mrmc_power(
        readers=8, cases=200, effect_size=1e-7, components=PILOT, alpha=0.05
    ).power
    assert tiny == pytest.approx(0.05, abs=1e-4)


def test_mrmc_power_monotone_in_cases_and_readers():
    p_small = core.mrmc_power(readers=8, cases=100, effect_size=0.05, components=PILOT).power
    p_big = core.mrmc_power(readers=8, cases=400, effect_size=0.05, components=PILOT).power
    p_more_readers = core.mrmc_power(
        readers=16, cases=100, effect_size=0.05, components=PILOT
    ).power
    assert p_small < p_big
    assert p_small < p_more_readers
    assert 0 < p_small < 1


def test_mrmc_scaling_rule():
    scaled = PILOT.scaled_to(200)
    assert scaled.var_error == pytest.approx(PILOT.var_error / 2)
    assert scaled.cov2 == pytest.approx(PILOT.cov2 / 2)
    assert scaled.var_treatment_reader == PILOT.var_treatment_reader


def test_mrmc_cases_needed_reaches_target():
    res = core.mrmc_cases_needed(
        readers=10, effect_size=0.05, components=PILOT, power=0.80, attrition_rate=0.0
    )
    assert res.max_power_at_limit is None
    assert res.achieved_power >= 0.80
    below = core.mrmc_power(
        readers=10, cases=res.cases_required - 1, effect_size=0.05, components=PILOT
    ).power
    assert below < 0.80


def test_mrmc_reader_variance_bounds_power():
    # a tiny effect with large reader×treatment variance cannot reach power by adding cases
    comps = core.ORVarianceComponents(
        var_treatment_reader=0.01,
        var_error=0.001,
        cov1=0.0004,
        cov2=0.0003,
        cov3=0.0002,
        pilot_cases=100,
    )
    res = core.mrmc_cases_needed(
        readers=4, effect_size=0.02, components=comps, power=0.80, max_cases=3000
    )
    assert res.max_power_at_limit is not None
    assert "readers" in res.notes[0].lower()


def test_mrmc_grid_cases_decrease_with_readers():
    grid = core.mrmc_reader_case_grid(effect_size=0.05, components=PILOT, reader_counts=[6, 12, 18])
    cases = [row["cases"] for row in grid.grid]
    assert all(c is not None for c in cases)
    assert cases[0] >= cases[1] >= cases[2]


def test_mrmc_rejects_invalid_components():
    bad = core.ORVarianceComponents(
        var_treatment_reader=0.0, var_error=0.001, cov1=0.001, cov2=0.001, cov3=0.0, pilot_cases=100
    )
    with pytest.raises(ValueError):
        core.mrmc_power(readers=5, cases=100, effect_size=0.05, components=bad)


# ── helpers ──────────────────────────────────────────────────────────────────


def test_attrition():
    assert core.adjust_for_attrition(90, 0.10) == 100
    assert core.adjust_for_attrition(100, 0.0) == 100
    with pytest.raises(ValueError):
        core.adjust_for_attrition(10, 1.0)


def test_allocate_strata_sums_to_total():
    alloc = core.allocate_strata(101, {"GE": 0.5, "Siemens": 0.3, "Philips": 0.2})
    assert sum(alloc.allocation.values()) == 101
    assert alloc.allocation["GE"] in (50, 51)
