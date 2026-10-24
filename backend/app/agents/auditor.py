"""Stage 5 — Compliance Auditor Agent: checklist-driven audit with revision requests."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..schemas.run import (
    SECTION_KEYS,
    AuditItemResult,
    AuditReport,
    DraftSection,
    RunStage,
    TriageDecision,
)
from .base import AgentContext, compact_json, truncate

SECTION_KEY_SET = [k for k, _, _ in SECTION_KEYS]

# checklist "section" vocabulary → protocol section keys
AFFINITY: list[tuple[tuple[str, ...], list[str]]] = [
    (("title", "abstract", "synopsis", "general"), ["synopsis"]),
    (
        ("background", "rationale", "introduction", "justification", "clinical association"),
        ["background"],
    ),
    (("objective", "hypothes"), ["objectives"]),
    (
        (
            "intervention",
            "index test",
            "device",
            "algorithm",
            "input",
            "model",
            "accountability",
            "change control",
            "變更",
            "產品描述",
            "輸入資料",
            "演算法",
        ),
        ["device"],
    ),
    (
        (
            "design",
            "setting",
            "procedure",
            "reader",
            "workflow",
            "triage",
            "效能驛證",
            "效能驗證",
            "monitoring",
            "risk categor",
            "analytical",
            "clinical validation",
        ),
        ["design"],
    ),
    (
        (
            "participant",
            "eligib",
            "population",
            "subject",
            "data independence",
            "sampling",
            "subgroup",
            "次族群",
            "本土",
        ),
        ["eligibility"],
    ),
    (("reference standard", "ground truth", "truthing", "參考標準"), ["ground_truth"]),
    (
        (
            "analysis",
            "statistic",
            "outcome",
            "sample size",
            "harms",
            "performance error",
            "效能指標",
            "results",
        ),
        ["statistics"],
    ),
    (
        (
            "data management",
            "confidential",
            "access",
            "code",
            "availability",
            "網路安全",
            "資料保護",
            "other information",
            "publication",
            "amendment",
        ),
        ["data_management"],
    ),
    (
        (
            "ethic",
            "consent",
            "irb",
            "regulat",
            "臨床試驳法規",
            "臨床試驗法規",
            "safety",
            "suspension",
            "registration",
            "funding",
            "conflict",
        ),
        ["ethics"],
    ),
]


def target_sections(item_section: str, prescreen_sections: list[str]) -> list[str]:
    s = item_section.lower()
    keys: list[str] = []
    for needles, targets in AFFINITY:
        if any(n in s for n in needles):
            keys.extend(targets)
    for p in prescreen_sections:
        if p in SECTION_KEY_SET and p not in keys:
            keys.append(p)
    if not keys:
        keys = ["synopsis", "design"]
    return keys[:3]


class ItemJudgement(BaseModel):
    item_id: str
    status: Literal["pass", "partial", "fail", "not_applicable"]
    evidence_sections: list[str] = Field(default_factory=list)
    finding: str
    fix_suggestion: str | None = None
    target_section_key: str | None = Field(
        default=None, description="One of the protocol section keys where the fix belongs"
    )


class JudgementBatch(BaseModel):
    judgements: list[ItemJudgement]


def _applicable_checklists(triage: TriageDecision | None, *, structural: bool = True) -> list[str]:
    ids: list[str] = []
    for c in triage.applicable_checklists if triage else []:
        if c.get("role") == "primary" or (structural and c.get("checklist_id") == "ISO14155-CIP"):
            ids.append(c["checklist_id"])
    if not ids:
        ids = ["STARD-AI", "ISO14155-CIP"]
    return ids


async def run_audit(
    ctx: AgentContext,
    sections: list[DraftSection],
    *,
    triage: TriageDecision | None,
    iteration: int,
) -> AuditReport:
    by_key = {s.key: s for s in sections}
    section_texts = {s.key: s.markdown for s in sections}
    checklist_ids = _applicable_checklists(triage)
    await ctx.progress("Audit: loading checklists", checklists=checklist_ids, iteration=iteration)

    # group (checklist, item) by primary target section so each LLM call sees only relevant text
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    item_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for cid in checklist_ids:
        cl = await ctx.mcp.try_call(
            "regulatory_rag", "get_checklist", {"checklist_id": cid}, warnings=ctx.state.warnings
        )
        if not cl:
            continue
        pre = (
            await ctx.mcp.try_call(
                "regulatory_rag",
                "prescreen_checklist_coverage",
                {"checklist_id": cid, "sections": section_texts},
                warnings=ctx.state.warnings,
            )
            or {}
        )
        pre_by_id = {p["item_id"]: p for p in pre.get("items", [])}
        for it in cl.get("items", []):
            p = pre_by_id.get(it["id"], {})
            targets = target_sections(it.get("section", ""), p.get("matched_sections", []))
            meta = {
                "checklist_id": cid,
                "item_id": it["id"],
                "section": it.get("section"),
                "text": it.get("text"),
                "prescreen": p.get("status"),
                "matched_keywords": p.get("matched_keywords", []),
                "candidate_sections": targets,
            }
            item_meta[(cid, it["id"])] = meta
            groups[targets[0]].append(meta)

    results: list[AuditItemResult] = []
    revision_requests: dict[str, list[str]] = defaultdict(list)
    system = ctx.system_prompt(
        "ROLE: Compliance Auditor Agent. Judge each checklist item against the supplied protocol sections ONLY. "
        "'pass' = fully and explicitly addressed; 'partial' = mentioned but incomplete/vague or marked [TO BE CONFIRMED]; "
        "'fail' = absent; 'not_applicable' = genuinely irrelevant to this design (explain). For partial/fail give a concrete, "
        "actionable fix_suggestion and the single best target_section_key. Be strict but fair; do not reward boilerplate."
    )
    for primary_key, metas in groups.items():
        # include the primary section plus the other candidate sections (deduplicated), truncated
        wanted: list[str] = [primary_key]
        for m in metas:
            for k in m["candidate_sections"]:
                if k not in wanted:
                    wanted.append(k)
        ctx_sections = {
            k: truncate(by_key[k].markdown, 7000 if k == primary_key else 3500)
            for k in wanted[:4]
            if k in by_key
        }
        user = (
            "PROTOCOL SECTIONS (Markdown):\n"
            + compact_json(ctx_sections)
            + "\n\nVALID target_section_key VALUES: "
            + ", ".join(SECTION_KEY_SET)
            + "\n\nCHECKLIST ITEMS TO JUDGE:\n"
            + compact_json(
                [{k: v for k, v in m.items() if k != "candidate_sections"} for m in metas], 9000
            )
            + "\n\nReturn one judgement per item (same item_id values)."
        )
        try:
            batch = await ctx.ask_json(
                system=system,
                user=user,
                model=JudgementBatch,
                max_tokens=ctx.settings.llm_section_max_tokens,
            )
        except Exception as exc:  # keep auditing other groups
            ctx.state.warnings.append(f"audit batch for {primary_key} failed: {exc}")
            continue
        judged = {j.item_id: j for j in batch.judgements}
        for m in metas:
            j = judged.get(m["item_id"])
            if j is None:
                results.append(
                    AuditItemResult(
                        checklist_id=m["checklist_id"],
                        item_id=m["item_id"],
                        item_text=m["text"],
                        status="partial",
                        finding="No judgement returned by the auditor model.",
                        fix_suggestion="Re-audit this item.",
                        evidence_sections=[],
                    )
                )
                continue
            tgt = j.target_section_key if j.target_section_key in SECTION_KEY_SET else primary_key
            results.append(
                AuditItemResult(
                    checklist_id=m["checklist_id"],
                    item_id=m["item_id"],
                    item_text=m["text"],
                    status=j.status,
                    evidence_sections=[s for s in j.evidence_sections if s in SECTION_KEY_SET],
                    finding=j.finding,
                    fix_suggestion=(
                        f"[{m['checklist_id']} {m['item_id']}] {j.fix_suggestion}"
                        if j.fix_suggestion
                        else None
                    ),
                )
            )
            if j.status in ("fail", "partial") and results[-1].fix_suggestion:
                results[-1].evidence_sections = results[-1].evidence_sections or [tgt]
                revision_requests[tgt].append(results[-1].fix_suggestion)

    n_pass = sum(r.status == "pass" for r in results)
    n_partial = sum(r.status == "partial" for r in results)
    n_fail = sum(r.status == "fail" for r in results)
    n_na = sum(r.status == "not_applicable" for r in results)
    verdict = (
        "compliant"
        if n_fail == 0 and n_partial <= max(2, len(results) // 10)
        else ("minor_revisions" if n_fail <= 2 else "major_revisions")
    )
    report = AuditReport(
        iteration=iteration,
        checklists_audited=checklist_ids,
        items=results,
        n_pass=n_pass,
        n_partial=n_partial,
        n_fail=n_fail,
        n_not_applicable=n_na,
        overall_verdict=verdict,
        revision_requests=dict(revision_requests),
    )
    await ctx.log(
        "Audit complete",
        RunStage.audit,
        iteration=iteration,
        verdict=verdict,
        n_fail=n_fail,
        n_partial=n_partial,
    )
    return report
