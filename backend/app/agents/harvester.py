"""Stage 2 — Evidence Harvester Agent (parallel MCP retrieval → Predicate Benchmark Matrix)."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from pydantic import BaseModel, Field

from ..schemas.run import BenchmarkRow, EvidenceItem, EvidenceMatrix, RunStage
from .base import AgentContext, compact_json, truncate
from .triage import rag_jurisdictions


class MatrixSynthesis(BaseModel):
    benchmark_rows: list[BenchmarkRow] = Field(min_length=3)
    narrative_summary: str
    baseline_performance: dict[str, Any] = Field(
        description="Numeric baselines extracted from the evidence, e.g. unaided_reader_sensitivity, unaided_reader_specificity, predicate_sensitivity_range, typical_cases, typical_readers; use null when unknown"
    )
    gaps_and_warnings: list[str]


# ── normalisers (defensive: every field optional) ────────────────────────────


def _trial_items(res: dict | None) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for s in (res or {}).get("studies", []) or []:
        di = s.get("design_info") or {}
        enr = s.get("enrollment") or {}
        design_bits = [
            s.get("study_type"),
            di.get("time_perspective"),
            di.get("observational_model"),
            di.get("allocation"),
            di.get("masking"),
        ]
        out.append(
            EvidenceItem(
                source="clinicaltrials",
                ref_id=s.get("nct_id", "?"),
                title=s.get("brief_title") or s.get("official_title") or "",
                url=s.get("url") or f"https://clinicaltrials.gov/study/{s.get('nct_id')}",
                summary=truncate("; ".join(s.get("conditions") or []), 300),
                design=" / ".join(str(b) for b in design_bits if b),
                sample_size=f"{enr.get('count')} ({enr.get('type')})" if enr.get("count") else None,
                endpoints=[o.get("measure", "") for o in (s.get("primary_outcomes") or [])][:6],
                raw={
                    "status": s.get("overall_status"),
                    "sponsor": s.get("lead_sponsor"),
                    "countries": s.get("countries"),
                },
            )
        )
    return out


def _predicate_items(bench: dict | None, records: dict | None) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    by_k = {d.get("k_number"): d for d in ((records or {}).get("devices") or [])}
    for dev in (bench or {}).get("devices", []) or []:
        ex = dev.get("extract") or {}
        k = dev.get("submission_number", "?")
        rec = by_k.get(k, {})
        metrics: dict[str, Any] = {}
        for m in ex.get("metrics", []) or []:
            metrics.setdefault(m.get("metric"), []).append(
                {"value": m.get("value"), "ci": [m.get("ci_lower"), m.get("ci_upper")]}
            )
        out.append(
            EvidenceItem(
                source="openfda",
                ref_id=k,
                title=rec.get("device_name") or f"FDA submission {k}",
                url=dev.get("summary_url"),
                summary=truncate(" ".join((ex.get("section_excerpts") or [])[:2]), 600)
                if dev.get("pdf_found")
                else "Summary PDF not available",
                design=", ".join(ex.get("design_keywords") or []) or None,
                sample_size=str(ex["n_cases"]) if ex.get("n_cases") else None,
                readers=str(ex["n_readers"]) if ex.get("n_readers") else None,
                reported_performance=metrics,
                ground_truth=truncate(" ".join(ex.get("ground_truth_sentences") or []), 400)
                or None,
                raw={
                    "pdf_found": dev.get("pdf_found"),
                    "confidence": ex.get("confidence"),
                    "applicant": rec.get("applicant"),
                    "decision_date": rec.get("decision_date"),
                    "product_code": rec.get("product_code"),
                    "predicates": ex.get("predicate_k_numbers"),
                },
            )
        )
    # devices found by search but not benchmarked
    for k, rec in by_k.items():
        if any(i.ref_id == k for i in out):
            continue
        out.append(
            EvidenceItem(
                source="openfda",
                ref_id=k or "?",
                title=rec.get("device_name") or "",
                url=rec.get("summary_pdf_url"),
                summary=f"{rec.get('applicant', '')} · cleared {rec.get('decision_date', '')} · product code {rec.get('product_code', '')}",
                raw={"from": "find_predicate_devices"},
                accepted=False,
            )
        )
    return out


def _pubmed_items(res: dict | None, *, tag: str) -> list[EvidenceItem]:
    out: list[EvidenceItem] = []
    for a in (res or {}).get("articles", []) or []:
        art = a.get("article") or {}
        ex = a.get("extract") or {}
        metrics: dict[str, Any] = {}
        for m in ex.get("metrics", []) or []:
            metrics.setdefault(m.get("metric"), []).append(
                {"value": m.get("value"), "ci": [m.get("ci_low"), m.get("ci_high")]}
            )
        sizes = [f"{s.get('n')} {s.get('unit')}" for s in (ex.get("sample_sizes") or [])[:2]]
        out.append(
            EvidenceItem(
                source="pubmed",
                ref_id=str(art.get("pmid", "?")),
                title=art.get("title") or "",
                url=a.get("url") or f"https://pubmed.ncbi.nlm.nih.gov/{art.get('pmid')}/",
                summary=truncate(a.get("citation") or "", 300),
                design=", ".join(ex.get("design_keywords") or []) or None,
                sample_size="; ".join(sizes) or None,
                readers=str(ex["reader_count"]) if ex.get("reader_count") else None,
                reported_performance=metrics,
                raw={
                    "kind": tag,
                    "year": art.get("year"),
                    "journal": art.get("journal"),
                    "has_ai_terms": ex.get("has_ai_terms"),
                },
            )
        )
    return out


def _rag_items(results: list[dict]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            source="regulatory_rag",
            ref_id=f"{r.get('document_id')}#{r.get('page') or r.get('heading') or ''}",
            title=r.get("citation") or r.get("title") or "",
            url=r.get("source_url"),
            summary=truncate(r.get("text") or "", 500),
            raw={"jurisdiction": r.get("jurisdiction"), "score": r.get("score")},
        )
        for r in results
    ]


def _keywords(text: str) -> str:
    """Short keyword phrase for openFDA device-name search (stop-word stripped)."""
    words = [
        w
        for w in re.findall(r"[A-Za-z]{4,}", text)
        if w.lower() not in {"acute", "with", "suspected", "patients", "adult", "adults"}
    ]
    return " ".join(words[:2]) or text[:30]


_MODALITY_TOKENS = [
    ("mammogra", "mammography"),
    ("tomosynthesis", "tomosynthesis"),
    ("chest x-ray", "chest X-ray"),
    ("chest radiograph", "chest radiograph"),
    ("x-ray", "X-ray"),
    ("radiograph", "radiograph"),
    ("cta", "CT angiography"),
    ("ct", "CT"),
    ("mri", "MRI"),
    ("mr ", "MRI"),
    ("ultrasound", "ultrasound"),
    ("sonograph", "ultrasound"),
    ("echocardiogra", "echocardiography"),
    ("fundus", "fundus photography"),
    ("oct", "optical coherence tomography"),
    ("endoscop", "endoscopy"),
    ("colonoscop", "colonoscopy"),
    ("dermoscop", "dermoscopy"),
    ("pathology", "pathology"),
    ("histolog", "histopathology"),
    ("ecg", "ECG"),
    ("electrocardiogra", "ECG"),
    ("eeg", "EEG"),
    ("ehr", "electronic health records"),
    ("pet", "PET"),
]


def simplify_disease(text: str) -> str:
    """'Acute intracranial hemorrhage (ICH)' → 'Acute intracranial hemorrhage' (search engines choke on parentheses)."""
    t = re.sub(r"\([^)]*\)", " ", text)
    t = re.sub(r"[^\w\s\-']", " ", t)
    return re.sub(r"\s+", " ", t).strip() or text.strip()


def disease_acronym(text: str) -> str | None:
    m = re.search(r"\(([A-Za-z]{2,8})\)", text)
    return m.group(1) if m else None


def simplify_modality(text: str) -> str | None:
    """'Non-contrast head CT (DICOM)' → 'CT'; returns None when no known modality is recognised."""
    low = f" {text.lower()} "
    for needle, canonical in _MODALITY_TOKENS:
        # left word boundary always; right boundary too for short tokens (ct, mri, oct, pet, ecg, eeg, ehr)
        pattern = (
            r"(?<![a-z])"
            + re.escape(needle.strip())
            + (r"(?![a-z])" if len(needle.strip()) <= 3 else "")
        )
        if re.search(pattern, low):
            return canonical
    return None


# ── main entry ───────────────────────────────────────────────────────────────


async def run_harvest(ctx: AgentContext) -> EvidenceMatrix:
    inp = ctx.input
    raw_disease = inp.device_profile.indications_for_use.target_disease
    disease = simplify_disease(raw_disease)
    acronym = disease_acronym(raw_disease)
    modality = simplify_modality(inp.ai_specifications.input_modality)
    settings = ctx.settings
    W = ctx.state.warnings
    mcp = ctx.mcp

    async def _search_with_fallbacks(
        server: str, tool: str, base: dict[str, Any], count_key: str
    ) -> dict | None:
        """Try (disease+modality) → (disease only) → (acronym) until something comes back."""
        variants: list[dict[str, Any]] = [
            {**base, "modality": modality} if modality else dict(base)
        ]
        if modality:
            variants.append(dict(base))
        if acronym:
            variants.append({**base, "disease" if "disease" in base else "condition": acronym})
        last: dict | None = None
        for args in variants:
            res = await mcp.try_call(server, tool, args, warnings=W)
            if res is None:
                return last
            last = res
            if res.get(count_key) or []:
                return res
        return last

    async def trials() -> dict | None:
        return await _search_with_fallbacks(
            "clinicaltrials",
            "search_samd_trials",
            {"condition": disease, "page_size": settings.harvest_max_trials},
            "studies",
        )

    async def predicate_bench() -> dict | None:
        if not inp.device_profile.predicate_devices:
            return None
        return await mcp.try_call(
            "openfda",
            "summarize_predicate_benchmarks",
            {
                "submission_numbers": inp.device_profile.predicate_devices[
                    : settings.harvest_max_predicates
                ]
            },
            warnings=W,
        )

    async def predicate_search() -> dict | None:
        args: dict[str, Any] = {"limit": settings.harvest_max_predicates}
        if inp.device_profile.product_code:
            args["product_code"] = inp.device_profile.product_code
        else:
            args["keyword"] = _keywords(disease)
        return await mcp.try_call("openfda", "find_predicate_devices", args, warnings=W)

    async def ai_list() -> dict | None:
        args: dict[str, Any] = {"limit": 15}
        if inp.device_profile.product_code:
            args["product_code"] = inp.device_profile.product_code
        else:
            args["keyword"] = _keywords(disease)
        return await mcp.try_call("openfda", "search_fda_ai_device_list", args, warnings=W)

    async def baseline() -> dict | None:
        metric = (
            inp.statistical_assumptions.primary_endpoints[0].value.lower()
            if inp.statistical_assumptions.primary_endpoints
            else None
        )
        return await _search_with_fallbacks(
            "pubmed",
            "search_baseline_performance",
            {
                "disease": disease,
                "metric": metric,
                "max_results": settings.harvest_max_articles,
                "exclude_ai": True,
            },
            "articles",
        )

    async def ai_evidence() -> dict | None:
        return await _search_with_fallbacks(
            "pubmed",
            "search_ai_evidence",
            {"disease": disease, "max_results": settings.harvest_max_articles},
            "articles",
        )

    async def guidance() -> list[dict]:
        hits: list[dict] = []
        topics = [
            "sample size justification reference standard",
            "reader study washout fully crossed",
            "subgroup analysis acquisition device site",
            "independence of test data from training data",
        ]
        for jur in rag_jurisdictions(inp.device_profile.target_jurisdictions)[:3]:
            for t in topics[:2]:
                res = await mcp.try_call(
                    "regulatory_rag",
                    "retrieve_guideline_clauses",
                    {
                        "query": f"{t} {inp.device_profile.samd_category.value}",
                        "jurisdiction": jur,
                        "top_k": 3,
                    },
                    warnings=W,
                )
                hits.extend((res or {}).get("results") or [])
        seen: set[str] = set()
        uniq: list[dict] = []
        for h in hits:
            key = f"{h.get('document_id')}:{h.get('page')}:{h.get('heading')}"
            if key not in seen:
                seen.add(key)
                uniq.append(h)
        return uniq

    await ctx.progress(
        "Harvest: querying ClinicalTrials.gov, openFDA, PubMed and the guidance index in parallel"
    )
    t_res, bench, p_search, ai_lst, base_res, ai_res, rag_hits = await asyncio.gather(
        trials(),
        predicate_bench(),
        predicate_search(),
        ai_list(),
        baseline(),
        ai_evidence(),
        guidance(),
    )

    items: list[EvidenceItem] = []
    items += _trial_items(t_res)
    items += _predicate_items(bench, p_search)
    for row in (ai_lst or {}).get("devices", []) or []:
        if any(i.ref_id == row.get("submission_number") for i in items):
            continue
        items.append(
            EvidenceItem(
                source="openfda",
                ref_id=row.get("submission_number", "?"),
                title=row.get("device_name", ""),
                url=row.get("summary_url"),
                summary=f"FDA AI-enabled device list · {row.get('company', '')} · {row.get('decision_date', '')} · panel {row.get('panel', '')} · {row.get('product_code', '')}",
                raw={"from": "fda_ai_device_list"},
                accepted=False,
            )
        )
    items += _pubmed_items(base_res, tag="baseline_unaided")
    items += _pubmed_items(ai_res, tag="ai_evidence")
    items += _rag_items(rag_hits)

    counts = {
        s: sum(1 for i in items if i.source == s)
        for s in ("clinicaltrials", "openfda", "pubmed", "regulatory_rag")
    }
    await ctx.progress("Harvest: evidence collected", **counts)

    # LLM synthesis of the benchmark matrix
    system = ctx.system_prompt(
        "ROLE: Evidence Harvester Agent. Build a *Predicate Benchmark Matrix* comparing the sponsor's proposed design "
        "against what predicates, registered trials and literature actually used. Rows must include at least: study design, "
        "sample size (positives/negatives or total), number of readers (if any), reference standard, primary endpoints / "
        "performance goals, subgroup strategy. Quote values with their ref_id (NCT…, K…, PMID…). Put numeric baselines useful "
        "for sample-size calculation into baseline_performance (unaided reader sensitivity/specificity, predicate sensitivity/"
        "specificity ranges, typical case counts). List evidence gaps explicitly."
    )
    slim = [
        {
            k: v
            for k, v in i.model_dump(mode="json").items()
            if k not in ("raw", "accepted", "user_note") and v not in (None, [], {}, "")
        }
        for i in items
        if i.accepted or i.source == "openfda"
    ]
    user = (
        "SPONSOR PROPOSED DESIGN (JSON):\n"
        + compact_json(inp, 5000)
        + "\n\nEVIDENCE ITEMS (JSON, truncated):\n"
        + compact_json(slim, 28000)
        + "\n\nPREDICATE AGGREGATE (from openFDA summaries):\n"
        + compact_json((bench or {}).get("aggregate"), 2000)
        + "\n\nTRIAL DESIGN PATTERNS:\n"
        + compact_json({"total_count": (t_res or {}).get("total_count")}, 500)
        + "\n\nProduce the benchmark matrix synthesis."
    )
    try:
        synth = await ctx.ask_json(
            system=system,
            user=user,
            model=MatrixSynthesis,
            max_tokens=ctx.settings.llm_section_max_tokens,
        )
        rows, narrative, baseline, gaps = (
            synth.benchmark_rows,
            synth.narrative_summary,
            synth.baseline_performance,
            synth.gaps_and_warnings,
        )
    except Exception as exc:  # the evidence list is still useful for the reviewer
        msg = f"benchmark matrix synthesis failed: {type(exc).__name__}: {str(exc)[:300]}"
        W.append(msg)
        await ctx.log(msg)
        rows, narrative, baseline, gaps = (
            [],
            "[TO BE CONFIRMED] Automatic synthesis failed; review the raw evidence items below.",
            {},
            [msg],
        )
    matrix = EvidenceMatrix(
        items=items,
        benchmark_rows=rows,
        narrative_summary=narrative,
        baseline_performance=baseline,
        gaps_and_warnings=gaps + [w for w in W if "failed" in w and w not in gaps],
    )
    await ctx.log(
        "Evidence matrix drafted — awaiting human confirmation",
        RunStage.harvest,
        n_items=len(items),
    )
    return matrix
