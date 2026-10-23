import pytest

from mcp_pubmed_evidence.extract import (
    extract_design_keywords,
    extract_metrics,
    extract_performance,
    extract_reader_count,
    extract_sample_sizes,
)


def _by_metric(mentions, name):
    return [m for m in mentions if m.metric == name]


def test_percent_with_ci_and_decimal_with_bracket_ci():
    text = (
        "Pooled reader sensitivity was 88.4% (95% CI, 85.1%–91.2%) and specificity was 93.0% "
        "(95% CI: 91.0–94.7). The area under the curve was 0.91 (0.89–0.93). Accuracy of 91.5% was observed."
    )
    m = extract_metrics(text)
    sens = _by_metric(m, "sensitivity")[0]
    assert sens.value == pytest.approx(0.884)
    assert (sens.ci_low, sens.ci_high) == (pytest.approx(0.851), pytest.approx(0.912))
    spec = _by_metric(m, "specificity")[0]
    assert spec.value == pytest.approx(0.93)
    assert (spec.ci_low, spec.ci_high) == (pytest.approx(0.91), pytest.approx(0.947))
    auc = _by_metric(m, "auc")[0]
    assert auc.value == pytest.approx(0.91)
    assert (auc.ci_low, auc.ci_high) == (pytest.approx(0.89), pytest.approx(0.93))
    acc = _by_metric(m, "accuracy")[0]
    assert acc.value == pytest.approx(0.915)
    assert acc.ci_low is None
    assert "sensitivity was 88.4%" in sens.context


def test_paired_statement_assigns_values_in_order():
    text = "Sensitivity and specificity were 0.76 and 0.94, respectively."
    m = extract_metrics(text)
    assert _by_metric(m, "sensitivity")[0].value == pytest.approx(0.76)
    assert _by_metric(m, "specificity")[0].value == pytest.approx(0.94)
    assert len(m) == 2


def test_paired_statement_with_percent_and_ci():
    text = "The sensitivity and specificity of radiologists were 93% (95% CI 90-95) and 85% (95% CI 82-88)."
    m = extract_metrics(text)
    sens = _by_metric(m, "sensitivity")[0]
    spec = _by_metric(m, "specificity")[0]
    assert (
        sens.value == pytest.approx(0.93)
        and sens.ci_low == pytest.approx(0.90)
        and sens.ci_high == pytest.approx(0.95)
    )
    assert (
        spec.value == pytest.approx(0.85)
        and spec.ci_low == pytest.approx(0.82)
        and spec.ci_high == pytest.approx(0.88)
    )


def test_auroc_aliases_and_lancet_middle_dot():
    text = "The AUROC reached 0·87 (95% CI 0·84–0·90); the c-statistic was 0.80."
    m = extract_metrics(text)
    aucs = _by_metric(m, "auc")
    assert aucs[0].value == pytest.approx(0.87)
    assert aucs[0].ci_low == pytest.approx(0.84)
    assert aucs[1].value == pytest.approx(0.80)


def test_ppv_npv_and_integers_without_percent_are_ignored():
    text = "The PPV was 71% and the negative predictive value was 0.98. Sensitivity in 2 of 3 readers improved."
    m = extract_metrics(text)
    assert _by_metric(m, "ppv")[0].value == pytest.approx(0.71)
    assert _by_metric(m, "npv")[0].value == pytest.approx(0.98)
    assert not _by_metric(m, "sensitivity")


def test_sample_sizes_n_eq_and_units():
    text = (
        "We included 1,250 consecutive head CT scans (n = 1,250) from 3 hospitals and 400 patients."
    )
    sizes = extract_sample_sizes(text)
    pairs = {(s.n, s.unit) for s in sizes}
    assert (1250, "n") in pairs
    assert (1250, "ct scans") in pairs or (1250, "scans") in pairs
    assert (400, "patients") in pairs


def test_reader_count_words_and_digits():
    assert extract_reader_count("Three emergency physicians reviewed the scans.") == 3
    assert extract_reader_count("12 board-certified radiologists independently interpreted") == 12
    assert extract_reader_count("No readers were involved") is None


def test_design_keywords_and_ai_flag():
    text = (
        "In this retrospective multicenter reader study (MRMC), a deep learning model was compared."
    )
    assert {"retrospective", "multicenter", "reader study", "MRMC"} <= set(
        extract_design_keywords(text)
    )
    perf = extract_performance(text)
    assert perf.has_ai_terms is True
    assert extract_performance("Radiologists read 100 cases.").has_ai_terms is False


def test_empty_text():
    perf = extract_performance("")
    assert perf.metrics == [] and perf.sample_sizes == [] and perf.reader_count is None
