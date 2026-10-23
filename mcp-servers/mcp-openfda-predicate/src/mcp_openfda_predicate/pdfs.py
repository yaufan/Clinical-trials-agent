"""510(k) summary / De Novo decision-summary PDFs: URL rules, retrieval and heuristic extraction.

accessdata.fda.gov answers 404 to requests without a browser-like ``User-Agent``; the fetch
helper therefore always sends one. A genuine 404 (no summary on file, or a 510(k) *statement*
instead of a summary) is reported as ``pdf_found=False`` rather than raised.
"""

from __future__ import annotations

import io
import re
import statistics
from typing import Literal

import httpx
from pydantic import BaseModel, Field
from pypdf import PdfReader

ACCESSDATA_BASE_URL = "https://www.accessdata.fda.gov/cdrh_docs"
BROWSER_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MAX_PDF_PAGES = 60

_K_RE = re.compile(r"^K(\d{2})(\d{4})$")
_DEN_RE = re.compile(r"^DEN(\d{6})$")


def normalise_k_number(k: str) -> str:
    k = k.strip().upper().replace(" ", "")
    if not _K_RE.match(k):
        raise ValueError(f"not a 510(k) number (expected K + 6 digits): {k!r}")
    return k


def k_number_to_summary_url(k_number: str, *, base_url: str = ACCESSDATA_BASE_URL) -> str:
    """K{YY}{NNNN} → ``.../cdrh_docs/pdf{YY}/K{YY}{NNNN}.pdf``.

    The folder suffix is the two-digit year without a leading zero (K083540 → pdf8). For the
    year 2000 (``K00xxxx``) and pre-2000 numbers (``K9xxxxx``) the folder is plain ``pdf``.
    """
    k = normalise_k_number(k_number)
    yy = int(k[1:3])
    if yy == 0 or yy >= 90:
        folder = "pdf"
    else:
        folder = f"pdf{yy}"
    return f"{base_url}/{folder}/{k}.pdf"


def den_number_to_summary_url(den_number: str, *, base_url: str = ACCESSDATA_BASE_URL) -> str:
    den = den_number.strip().upper().replace(" ", "")
    if not _DEN_RE.match(den):
        raise ValueError(f"not a De Novo number (expected DEN + 6 digits): {den!r}")
    return f"{base_url}/reviews/{den}.pdf"


class PdfFetchResult(BaseModel):
    url: str
    found: bool
    status_code: int
    pages: int = 0
    text: str = ""
    truncated: bool = False
    error: str | None = None


def pdf_bytes_to_text(data: bytes, *, max_pages: int = MAX_PDF_PAGES) -> tuple[str, int, bool]:
    """Return (text, total_pages, truncated)."""
    reader = PdfReader(io.BytesIO(data))
    total = len(reader.pages)
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        if i >= max_pages:
            break
        try:
            parts.append(page.extract_text() or "")
        except Exception:  # pragma: no cover - corrupt page
            parts.append("")
    return "\n".join(parts), total, total > max_pages


async def fetch_pdf_text(
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    request_timeout: float = 60.0,
    max_pages: int = MAX_PDF_PAGES,
) -> PdfFetchResult:
    owns = client is None
    client = client or httpx.AsyncClient(timeout=request_timeout, follow_redirects=True)
    try:
        resp = await client.get(
            url, headers={"User-Agent": BROWSER_USER_AGENT, "Accept": "application/pdf,*/*"}
        )
        if resp.status_code == 404:
            return PdfFetchResult(url=url, found=False, status_code=404)
        if resp.status_code >= 400:
            return PdfFetchResult(
                url=url, found=False, status_code=resp.status_code, error=f"HTTP {resp.status_code}"
            )
        content = resp.content
        if not content.lstrip().startswith(b"%PDF"):
            return PdfFetchResult(
                url=url, found=False, status_code=resp.status_code, error="response is not a PDF"
            )
        try:
            text, pages, truncated = pdf_bytes_to_text(content, max_pages=max_pages)
        except Exception as exc:  # pragma: no cover - malformed PDF
            return PdfFetchResult(
                url=url, found=True, status_code=resp.status_code, error=f"PDF parse failed: {exc}"
            )
        return PdfFetchResult(
            url=url,
            found=True,
            status_code=resp.status_code,
            pages=pages,
            text=text,
            truncated=truncated,
        )
    except httpx.HTTPError as exc:
        return PdfFetchResult(
            url=url, found=False, status_code=0, error=f"{type(exc).__name__}: {exc}"
        )
    finally:
        if owns:
            await client.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic extraction
# ─────────────────────────────────────────────────────────────────────────────


class MetricMention(BaseModel):
    metric: Literal["sensitivity", "specificity", "auc", "ppv", "npv", "accuracy"]
    value: float = Field(description="As a proportion in [0, 1]")
    ci_lower: float | None = None
    ci_upper: float | None = None
    context: str


class CountMention(BaseModel):
    kind: Literal[
        "cases",
        "patients",
        "images",
        "studies",
        "exams",
        "readers",
        "sites",
        "positives",
        "negatives",
    ]
    value: int
    context: str


class ClinicalSummaryExtract(BaseModel):
    source_url: str | None = None
    pdf_found: bool = True
    pages: int = 0
    section_excerpts: list[str] = Field(
        default_factory=list, description="Text under clinical/performance headings"
    )
    metrics: list[MetricMention] = Field(default_factory=list)
    counts: list[CountMention] = Field(default_factory=list)
    n_cases: int | None = Field(
        default=None, description="Best guess of the test-set size (cases/patients/exams)"
    )
    n_readers: int | None = None
    n_sites: int | None = None
    ground_truth_sentences: list[str] = Field(default_factory=list)
    design_keywords: list[str] = Field(default_factory=list)
    predicate_k_numbers: list[str] = Field(default_factory=list)
    performance_goal_sentences: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    notes: list[str] = Field(default_factory=list)


_WS_RE = re.compile(r"[ \t ]+")
_HEADING_RE = re.compile(
    r"(?im)^[^\n]{0,12}(clinical\s+(?:performance|testing|study|studies|data|validation|information)"
    r"|performance\s+(?:testing|data|characteristics|assessment|evaluation)"
    r"|standalone\s+performance|stand-alone\s+performance|reader\s+study|mrmc"
    r"|summary\s+of\s+(?:clinical|performance))[^\n]{0,60}$"
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")
_METRIC_WORDS = {
    "sensitivity": "sensitivity",
    "specificity": "specificity",
    "auc": "auc",
    "auroc": "auc",
    "area under the curve": "auc",
    "area under the roc curve": "auc",
    "ppv": "ppv",
    "positive predictive value": "ppv",
    "npv": "npv",
    "negative predictive value": "npv",
    "accuracy": "accuracy",
}
_METRIC_RE = re.compile(
    r"(?i)\b(sensitivity|specificity|auroc|auc|area under the (?:roc )?curve|ppv|npv|positive predictive value|negative predictive value|accuracy)\b"
    r"[^.%\d]{0,60}?(?:of|was|were|=|:|is|at|achieved|reached|demonstrated)?\s*"
    r"(\d{1,3}(?:\.\d+)?)\s*(%)?"
    r"(?:\s*\(\s*95\s*%?\s*CI[:\s]*(\d{1,3}(?:\.\d+)?)\s*%?\s*[-–,to]+\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*\))?"
)
_WORD_NUMBERS = {
    w: i
    for i, w in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ]
    )
}
_COUNT_STOP_WORDS = {
    "and",
    "or",
    "of",
    "with",
    "from",
    "in",
    "on",
    "for",
    "to",
    "by",
    "at",
    "were",
    "was",
    "the",
    "a",
    "an",
    "that",
    "which",
    "per",
    "each",
    "versus",
    "vs",
}
_COUNT_RE = re.compile(
    r"(?i)\b(\d{1,3}(?:,\d{3})+|\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+((?:[A-Za-z][A-Za-z\-\.]*\s+){0,5}?)"
    r"(cases?|patients?|images?|studies|exams?|examinations?|scans?|readers?|radiologists?|physicians?|clinicians?|sites?|centers?|centres?|institutions?|hospitals?|positives?|negatives?)\b"
)
_READERS_WORDS = {
    "readers",
    "reader",
    "radiologists",
    "radiologist",
    "physicians",
    "physician",
    "clinicians",
    "clinician",
}
_SITES_WORDS = {
    "sites",
    "site",
    "centers",
    "center",
    "centres",
    "centre",
    "institutions",
    "institution",
    "hospitals",
    "hospital",
}
_CASES_WORDS = {
    "cases",
    "case",
    "patients",
    "patient",
    "images",
    "image",
    "studies",
    "exams",
    "exam",
    "examinations",
    "examination",
    "scans",
    "scan",
}
_GT_RE = re.compile(
    r"(?i)(ground[\s-]?truth|reference standard|gold standard|truth(?:ing)? (?:panel|process)|adjudicat\w+|consensus|pathology[\s-]confirmed|biopsy[\s-]confirmed|histopatholog\w+|majority (?:vote|agreement|rule))"
)
_DESIGN_TERMS: dict[str, re.Pattern[str]] = {
    "retrospective": re.compile(r"(?i)\bretrospective\w*"),
    "prospective": re.compile(r"(?i)\bprospective\w*"),
    "multicenter": re.compile(r"(?i)\bmulti[\s-]?(?:center|centre|site)\w*|\bmultisite\b"),
    "multi-reader": re.compile(r"(?i)\bmulti[\s-]?reader\w*|\bMRMC\b"),
    "standalone": re.compile(r"(?i)\bstand[\s-]?alone\b"),
    "fully-crossed": re.compile(r"(?i)\bfully[\s-]?crossed\b"),
    "washout": re.compile(r"(?i)\bwash[\s-]?out\b"),
    "blinded": re.compile(r"(?i)\bblind(?:ed|ing)\b"),
    "enriched": re.compile(r"(?i)\benrich(?:ed|ment)\b"),
    "consecutive": re.compile(r"(?i)\bconsecutive(?:ly)?\b"),
    "reader-study": re.compile(r"(?i)\breader (?:study|studies|comparison)\b"),
    "triage": re.compile(r"(?i)\btriage\b"),
    "performance-goal": re.compile(r"(?i)\bperformance goals?\b"),
    "non-inferiority": re.compile(r"(?i)\bnon[\s-]?inferior\w*"),
    "superiority": re.compile(r"(?i)\bsuperior(?:ity)?\b"),
    "subgroup": re.compile(r"(?i)\bsub[\s-]?group\w*|\bstratif\w+"),
}
_PREDICATE_K_RE = re.compile(r"\bK\s?(\d{6})\b")
_PERF_GOAL_RE = re.compile(
    r"(?i)performance goal|pre-?specified (?:primary )?endpoints?|primary endpoints?|acceptance criteri"
)


def normalise_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _to_proportion(v: float, percent_sign: bool) -> float | None:
    if percent_sign or v > 1.0:
        if v > 100:
            return None
        return round(v / 100.0, 4)
    return round(v, 4)


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s*\n\s*", " ", text)
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(flat) if s.strip()]


def extract_section_excerpts(
    text: str, *, max_chars: int = 2500, max_sections: int = 6
) -> list[str]:
    excerpts: list[str] = []
    for m in _HEADING_RE.finditer(text):
        start = m.start()
        chunk = text[start : start + max_chars].strip()
        if chunk and not any(chunk[:200] in e for e in excerpts):
            excerpts.append(chunk)
        if len(excerpts) >= max_sections:
            break
    return excerpts


def extract_metrics(text: str) -> list[MetricMention]:
    out: list[MetricMention] = []
    seen: set[tuple[str, float]] = set()
    flat = re.sub(r"\s*\n\s*", " ", text)
    for m in _METRIC_RE.finditer(flat):
        word = m.group(1).lower()
        metric = _METRIC_WORDS.get(word)
        if metric is None:
            continue
        pct = bool(m.group(3))
        val = _to_proportion(float(m.group(2)), pct)
        if val is None or val <= 0 or val > 1:
            continue
        lo = hi = None
        if m.group(4) and m.group(5):
            lo = _to_proportion(float(m.group(4)), pct or float(m.group(4)) > 1)
            hi = _to_proportion(float(m.group(5)), pct or float(m.group(5)) > 1)
        key = (metric, val)
        if key in seen:
            continue
        seen.add(key)
        ctx = flat[max(0, m.start() - 80) : m.end() + 80].strip()
        out.append(MetricMention(metric=metric, value=val, ci_lower=lo, ci_upper=hi, context=ctx))
    return out


def extract_counts(text: str) -> list[CountMention]:
    out: list[CountMention] = []
    flat = re.sub(r"\s*\n\s*", " ", text)
    for m in _COUNT_RE.finditer(flat):
        raw_n = m.group(1).replace(",", "").lower()
        n = _WORD_NUMBERS.get(raw_n) if raw_n.isalpha() else int(raw_n)
        if n is None:
            continue
        modifiers = [w.lower().strip(".") for w in m.group(2).split()]
        noun = m.group(3).lower()
        if n < 2:
            continue
        # a stop word between the number and the noun means we have jumped into another clause
        if any(w in _COUNT_STOP_WORDS for w in modifiers):
            continue
        if noun in _READERS_WORDS:
            kind = "readers"
        elif noun in _SITES_WORDS:
            kind = "sites"
        elif noun.startswith("positive") or any(w.startswith("positive") for w in modifiers):
            kind = "positives"
        elif noun.startswith("negative") or any(w.startswith("negative") for w in modifiers):
            kind = "negatives"
        elif noun.startswith("patient"):
            kind = "patients"
        elif noun.startswith("image"):
            kind = "images"
        elif noun.startswith("stud"):
            kind = "studies"
        elif noun.startswith("exam"):
            kind = "exams"
        else:
            kind = "cases"
        ctx = flat[max(0, m.start() - 60) : m.end() + 60].strip()
        out.append(CountMention(kind=kind, value=n, context=ctx))
    return out


def extract_ground_truth_sentences(text: str, *, limit: int = 6) -> list[str]:
    out: list[str] = []
    for s in _sentences(text):
        if _GT_RE.search(s) and 30 <= len(s) <= 600:
            if s not in out:
                out.append(s)
        if len(out) >= limit:
            break
    return out


def extract_performance_goal_sentences(text: str, *, limit: int = 5) -> list[str]:
    out: list[str] = []
    for s in _sentences(text):
        if _PERF_GOAL_RE.search(s) and 20 <= len(s) <= 600 and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def extract_design_keywords(text: str) -> list[str]:
    return [k for k, rx in _DESIGN_TERMS.items() if rx.search(text)]


def extract_predicate_k_numbers(text: str, *, exclude: str | None = None) -> list[str]:
    found: list[str] = []
    for m in _PREDICATE_K_RE.finditer(text):
        k = f"K{m.group(1)}"
        if exclude and k == exclude.upper():
            continue
        if k not in found:
            found.append(k)
    return found


def _best_count(counts: list[CountMention], kinds: set[str]) -> int | None:
    vals = [c.value for c in counts if c.kind in kinds]
    if not vals:
        return None
    # The test set is usually the largest "cases/patients/exams" figure quoted in the
    # performance section but tiny numbers (e.g. "3 radiologists") must not leak in.
    return max(vals)


def extract_clinical_summary(
    text: str, *, source_url: str | None = None, pages: int = 0, own_k_number: str | None = None
) -> ClinicalSummaryExtract:
    """Deterministic, regex-based extraction of clinical-validation facts from summary text."""
    norm = normalise_text(text)
    excerpts = extract_section_excerpts(norm)
    focus = "\n".join(excerpts) if excerpts else norm
    metrics = extract_metrics(focus) or extract_metrics(norm)
    counts = extract_counts(focus) or extract_counts(norm)
    gt = extract_ground_truth_sentences(focus) or extract_ground_truth_sentences(norm)
    goals = extract_performance_goal_sentences(focus) or extract_performance_goal_sentences(norm)
    design = extract_design_keywords(norm)
    predicates = extract_predicate_k_numbers(norm, exclude=own_k_number)

    reader_vals = [c.value for c in counts if c.kind == "readers" and c.value <= 200]
    n_readers = max(reader_vals) if reader_vals else None
    site_vals = [c.value for c in counts if c.kind == "sites" and c.value <= 500]
    n_sites = max(site_vals) if site_vals else None
    n_cases = _best_count(counts, {"cases", "patients", "exams", "studies", "images"})
    if n_cases is None:
        pos = _best_count(counts, {"positives"})
        neg = _best_count(counts, {"negatives"})
        if pos and neg:
            n_cases = pos + neg

    score = sum(
        [
            bool(excerpts),
            bool(metrics),
            n_cases is not None,
            n_readers is not None,
            bool(gt),
            bool(design),
        ]
    )
    confidence: Literal["low", "medium", "high"] = (
        "high" if score >= 5 else "medium" if score >= 3 else "low"
    )
    notes = [
        "Regex-based extraction from PDF text; verify every number against the source document.",
    ]
    if not excerpts:
        notes.append(
            "No clinical/performance heading detected; metrics were searched in the full text."
        )
    return ClinicalSummaryExtract(
        source_url=source_url,
        pdf_found=True,
        pages=pages,
        section_excerpts=excerpts,
        metrics=metrics,
        counts=counts[:40],
        n_cases=n_cases,
        n_readers=n_readers,
        n_sites=n_sites,
        ground_truth_sentences=gt,
        design_keywords=design,
        predicate_k_numbers=predicates[:10],
        performance_goal_sentences=goals,
        confidence=confidence,
        notes=notes,
    )


class BenchmarkAggregate(BaseModel):
    devices_requested: int
    devices_with_summary: int
    median_cases: float | None = None
    cases_range: tuple[int, int] | None = None
    median_readers: float | None = None
    readers_range: tuple[int, int] | None = None
    sensitivity_range: tuple[float, float] | None = None
    specificity_range: tuple[float, float] | None = None
    auc_range: tuple[float, float] | None = None
    design_keyword_frequency: dict[str, int] = Field(default_factory=dict)


def aggregate_benchmarks(extracts: list[ClinicalSummaryExtract]) -> BenchmarkAggregate:
    found = [e for e in extracts if e.pdf_found]
    cases = [e.n_cases for e in found if e.n_cases]
    readers = [e.n_readers for e in found if e.n_readers]

    def rng(metric: str) -> tuple[float, float] | None:
        vals = [m.value for e in found for m in e.metrics if m.metric == metric]
        return (min(vals), max(vals)) if vals else None

    freq: dict[str, int] = {}
    for e in found:
        for k in e.design_keywords:
            freq[k] = freq.get(k, 0) + 1
    return BenchmarkAggregate(
        devices_requested=len(extracts),
        devices_with_summary=len(found),
        median_cases=statistics.median(cases) if cases else None,
        cases_range=(min(cases), max(cases)) if cases else None,
        median_readers=statistics.median(readers) if readers else None,
        readers_range=(min(readers), max(readers)) if readers else None,
        sensitivity_range=rng("sensitivity"),
        specificity_range=rng("specificity"),
        auc_range=rng("auc"),
        design_keyword_frequency=dict(sorted(freq.items(), key=lambda kv: -kv[1])),
    )
