"""Deterministic extraction of diagnostic-performance figures from abstract text.

This is intentionally regex-based (no LLM) so that the numbers the biostatistician agent
anchors a sample-size calculation on can be traced back to a literal sentence in the source.
Recall is imperfect by design; precision is favoured.
"""

from __future__ import annotations

import re

from .models import MetricMention, MetricName, PerformanceExtract, SampleSizeMention

# ── value tokens ─────────────────────────────────────────────────────────────
# percent (93%, 93.1 %), decimal proportion (0.93, ·93, 1.00) or a decimal number ≥ 10
# that is almost certainly a percentage written without the sign (93.1).
_VAL = r"(?:\d{1,3}(?:[.·]\d+)?\s?%|(?:0?[.·]\d+|1[.·]0+)(?![\d%])|\d{2,3}[.·]\d+(?![\d%]))"
_RANGE_SEP = r"(?:–|—|−|-|to|,)"

_METRIC_ALIASES: list[tuple[MetricName, str]] = [
    ("sensitivity", r"sensitivit(?:y|ies)"),
    ("specificity", r"specificit(?:y|ies)"),
    (
        "auc",
        r"(?:AUROC|AUCs?|area under the (?:receiver[- ]operating[- ]characteristic |ROC )?curves?|c[- ]statistic)",
    ),
    ("accuracy", r"(?:diagnostic |overall )?accurac(?:y|ies)"),
    ("ppv", r"(?:PPVs?|positive predictive values?)"),
    ("npv", r"(?:NPVs?|negative predictive values?)"),
    ("f1", r"F1(?:[- ]scores?)?"),
    ("dice", r"Dice(?: similarity)?(?: coefficients?| scores?)?"),
]
_METRIC_UNION = "|".join(f"(?P<{name}>{pat})" for name, pat in _METRIC_ALIASES)

# "<metric> [filler without digits/sentence breaks] <value>"
_SINGLE_RE = re.compile(
    rf"\b(?:{_METRIC_UNION})\b(?P<filler>[^.;:\d%]{{0,40}}?)(?P<value>{_VAL})",
    re.IGNORECASE,
)

# "<metric A> and <metric B> (of|were|was) <value A> and <value B>"
_PAIR_RE = re.compile(
    rf"\b(?P<m1>{'|'.join(p for _, p in _METRIC_ALIASES)})\b\s*(?:and|/|,)\s*"
    rf"\b(?P<m2>{'|'.join(p for _, p in _METRIC_ALIASES)})\b"
    rf"(?P<filler>[^.;\d%]{{0,40}}?)(?P<v1>{_VAL})\s*(?:\((?P<ci1>[^()]*)\))?\s*(?:and|/|,|vs\.?|versus)\s*(?P<v2>{_VAL})",
    re.IGNORECASE,
)

# confidence interval immediately following a value; inside a CI plain integers are unambiguous
_CI_VAL = r"(?:\d{1,3}(?:[.·]\d+)?\s?%?)"
_CI_RE = re.compile(
    rf"^[\s,;]*(?:\(|\[)\s*(?:95\s?%\s?(?:CI|confidence intervals?)\s*[:,=]?\s*)?"
    rf"(?P<lo>{_CI_VAL})\s*{_RANGE_SEP}\s*(?P<hi>{_CI_VAL})\s*(?:\)|\])",
    re.IGNORECASE,
)
_CI_UNBRACKETED_RE = re.compile(
    rf"^[\s,;]*95\s?%\s?(?:CI|confidence intervals?)\s*[:,=]?\s*"
    rf"(?P<lo>{_CI_VAL})\s*{_RANGE_SEP}\s*(?P<hi>{_CI_VAL})",
    re.IGNORECASE,
)

_N_EQ_RE = re.compile(r"\bn\s?=\s?(?P<n>\d{1,3}(?:,\d{3})+|\d+)", re.IGNORECASE)
_UNITS = (
    "patients|participants|subjects|individuals|women|men|children|cases|images|scans|"
    "examinations|exams|lesions|nodules|studies|radiographs|mammograms|CT scans|"
    "chest radiographs|eyes|slides|ECGs|recordings|biopsies"
)
_NUMBER_WORD_RE = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)"
)
# up to three descriptive words ("consecutive head", "board-certified") that are not numbers
_SKIP_WORDS = rf"(?:(?!{_NUMBER_WORD_RE}\b)[A-Za-z][A-Za-z-]*\s+){{0,3}}?"
_N_UNIT_RE = re.compile(
    rf"\b(?P<n>\d{{1,3}}(?:,\d{{3}})+|\d{{2,7}})\s+{_SKIP_WORDS}(?P<unit>{_UNITS})\b",
    re.IGNORECASE,
)
_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
}
_READERS_RE = re.compile(
    rf"\b(?P<n>\d{{1,3}}|{_NUMBER_WORD_RE})\s+{_SKIP_WORDS}"
    r"(?P<who>radiologists?|readers?|physicians?|observers?|clinicians?|pathologists?|ophthalmologists?|"
    r"dermatologists?|cardiologists?|neurologists?|endoscopists?|gastroenterologists?|experts?)\b",
    re.IGNORECASE,
)
_DESIGN_TERMS: list[tuple[str, str]] = [
    ("retrospective", r"\bretrospective(?:ly)?\b"),
    ("prospective", r"\bprospective(?:ly)?\b"),
    ("multicenter", r"\bmulti[- ]?cent(?:er|re)\b"),
    ("single-center", r"\bsingle[- ]cent(?:er|re)\b"),
    ("reader study", r"\breader (?:study|studies)\b"),
    ("MRMC", r"\b(?:MRMC|multi[- ]?reader,? multi[- ]?case)\b"),
    ("randomized", r"\brandomi[sz]ed\b"),
    ("consecutive", r"\bconsecutive\b"),
    ("external validation", r"\bexternal(?:ly)? validat(?:ion|ed)\b"),
    ("crossover", r"\bcross[- ]?over\b"),
    ("meta-analysis", r"\bmeta[- ]?analysis\b"),
    ("systematic review", r"\bsystematic review\b"),
]
_AI_RE = re.compile(
    r"\b(?:deep learning|artificial intelligence|machine learning|convolutional|neural network|"
    r"computer[- ]aided|\bAI\b|CNN|transformer model)\b",
    re.IGNORECASE,
)


def _to_proportion(token: str) -> float:
    t = token.replace("·", ".").replace(" ", "")
    if t.endswith("%"):
        return round(float(t[:-1]) / 100.0, 6)
    v = float(t)
    return round(v / 100.0, 6) if v > 1.0 else round(v, 6)


def _snippet(text: str, start: int, end: int, width: int = 90) -> str:
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    return prefix + " ".join(text[lo:hi].split()) + suffix


def _metric_name(match_text: str) -> MetricName | None:
    for name, pat in _METRIC_ALIASES:
        if re.fullmatch(pat, match_text, re.IGNORECASE):
            return name
    return None


def _parse_ci(text: str, pos: int) -> tuple[float | None, float | None, int]:
    tail = text[pos : pos + 80]
    for rx in (_CI_RE, _CI_UNBRACKETED_RE):
        m = rx.match(tail)
        if m:
            lo, hi = _to_proportion(m.group("lo")), _to_proportion(m.group("hi"))
            if lo <= hi:
                return lo, hi, pos + m.end()
    return None, None, pos


def extract_metrics(text: str) -> list[MetricMention]:
    """Find metric values (with CIs when adjacent) in free text."""
    if not text:
        return []
    mentions: list[MetricMention] = []
    used_spans: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        return any(not (b <= s or a >= e) for s, e in used_spans)

    # paired statements first: "sensitivity and specificity were 93% and 85%"
    for m in _PAIR_RE.finditer(text):
        n1, n2 = _metric_name(m.group("m1")), _metric_name(m.group("m2"))
        if n1 is None or n2 is None or n1 == n2:
            continue
        v1_start, v1_end = m.start("v1"), m.end("v1")
        v2_end = m.end("v2")
        lo1, hi1, _ = _parse_ci(text, v1_end)
        lo2, hi2, end2 = _parse_ci(text, v2_end)
        ctx = _snippet(text, m.start(), end2)
        mentions.append(
            MetricMention(
                metric=n1,
                value=_to_proportion(m.group("v1")),
                ci_low=lo1,
                ci_high=hi1,
                as_reported=m.group("v1").strip(),
                context=ctx,
            )
        )
        mentions.append(
            MetricMention(
                metric=n2,
                value=_to_proportion(m.group("v2")),
                ci_low=lo2,
                ci_high=hi2,
                as_reported=m.group("v2").strip(),
                context=ctx,
            )
        )
        used_spans.append((m.start(), end2))
        used_spans.append((v1_start, v1_end))

    for m in _SINGLE_RE.finditer(text):
        v_start, v_end = m.start("value"), m.end("value")
        if overlaps(v_start, v_end):
            continue
        name = next((n for n, _ in _METRIC_ALIASES if m.group(n)), None)
        if name is None:
            continue
        lo, hi, end = _parse_ci(text, v_end)
        value = _to_proportion(m.group("value"))
        if not 0.0 <= value <= 1.0:
            continue
        mentions.append(
            MetricMention(
                metric=name,
                value=value,
                ci_low=lo,
                ci_high=hi,
                as_reported=m.group("value").strip(),
                context=_snippet(text, m.start(), end),
            )
        )
        used_spans.append((v_start, v_end))

    # de-duplicate identical (metric, value, context) triples
    seen: set[tuple[str, float, str]] = set()
    unique: list[MetricMention] = []
    for mm in mentions:
        key = (mm.metric, mm.value, mm.as_reported)
        if key in seen:
            continue
        seen.add(key)
        unique.append(mm)
    return unique


def extract_sample_sizes(text: str) -> list[SampleSizeMention]:
    out: list[SampleSizeMention] = []
    seen: set[tuple[int, str]] = set()
    for m in _N_EQ_RE.finditer(text):
        n = int(m.group("n").replace(",", ""))
        if (n, "n") not in seen:
            seen.add((n, "n"))
            out.append(
                SampleSizeMention(n=n, unit="n", context=_snippet(text, m.start(), m.end(), 60))
            )
    for m in _N_UNIT_RE.finditer(text):
        n = int(m.group("n").replace(",", ""))
        unit = m.group("unit").lower()
        # skip obvious years ("2019 patients" is implausible but "2019" alone is excluded by the unit requirement)
        if (n, unit) in seen:
            continue
        seen.add((n, unit))
        out.append(
            SampleSizeMention(n=n, unit=unit, context=_snippet(text, m.start(), m.end(), 60))
        )
    return out


def extract_reader_count(text: str) -> int | None:
    best: int | None = None
    for m in _READERS_RE.finditer(text):
        tok = m.group("n").lower()
        n = _NUMBER_WORDS.get(tok) if not tok.isdigit() else int(tok)
        if n is None or n <= 0 or n > 500:
            continue
        best = n if best is None else max(best, n)
    return best


def extract_design_keywords(text: str) -> list[str]:
    found = [label for label, pat in _DESIGN_TERMS if re.search(pat, text, re.IGNORECASE)]
    return found


def extract_performance(text: str) -> PerformanceExtract:
    """Run every extractor on a block of text (title + abstract is the usual input)."""
    text = text or ""
    return PerformanceExtract(
        metrics=extract_metrics(text),
        sample_sizes=extract_sample_sizes(text),
        reader_count=extract_reader_count(text),
        design_keywords=extract_design_keywords(text),
        has_ai_terms=bool(_AI_RE.search(text)),
    )
