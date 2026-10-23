"""Structured reporting / regulatory checklists and deterministic coverage pre-screening."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CHECKLIST_DIR = Path(__file__).parent / "checklists"

DesignType = Literal[
    "Standalone_Performance",
    "MRMC_Reader_Study",
    "Hybrid_Standalone_and_MRMC",
    "Prospective_Interventional_RCT",
]


class ChecklistItem(BaseModel):
    id: str
    section: str
    type: str
    text: str
    keywords: list[str] = Field(default_factory=list)
    note: str | None = None


class Checklist(BaseModel):
    id: str
    title: str
    applies_to: list[str] = Field(default_factory=list)
    scope_note: str | None = None
    items: list[ChecklistItem]
    source_file: str


@lru_cache(maxsize=1)
def load_all() -> dict[str, Checklist]:
    out: dict[str, Checklist] = {}
    for path in sorted(CHECKLIST_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cl = Checklist(**data, source_file=path.name)
        out[cl.id] = cl
    return out


def get_checklist(checklist_id: str) -> Checklist:
    all_ = load_all()
    key = checklist_id.upper().replace("_", "-")
    for k, v in all_.items():
        if k.upper() == key:
            return v
    raise KeyError(f"unknown checklist {checklist_id!r}; available: {sorted(all_)}")


class ChecklistSelection(BaseModel):
    checklist_id: str
    role: Literal["primary", "supporting", "structural"]
    rationale: str


def select_checklists(
    design_type: str,
    samd_category: str | None = None,
    jurisdictions: list[str] | None = None,
) -> list[ChecklistSelection]:
    """Deterministic mapping from study design / device category / markets to checklists.

    The key correction over naive 'always SPIRIT-AI' logic: SPIRIT-AI is for *interventional
    clinical trial protocols*; standalone and reader studies are diagnostic-accuracy designs
    and are governed by STARD-AI (reporting) plus ISO 14155 Annex A (plan structure).
    """
    j = {x.upper() for x in (jurisdictions or [])}
    cat = (samd_category or "").lower()
    sel: list[ChecklistSelection] = []

    if "prognostic" in cat or "predictive" in cat:
        sel.append(
            ChecklistSelection(
                checklist_id="TRIPOD-AI",
                role="primary",
                rationale="Prognostic/predictive model validation is a prediction-model study (TRIPOD+AI).",
            )
        )
    if design_type in ("Standalone_Performance", "MRMC_Reader_Study", "Hybrid_Standalone_and_MRMC"):
        sel.append(
            ChecklistSelection(
                checklist_id="STARD-AI",
                role="primary",
                rationale="Standalone and reader studies are diagnostic test accuracy designs (STARD-AI / STARD 2015).",
            )
        )
    if design_type in ("Prospective_Interventional_RCT", "Hybrid_Standalone_and_MRMC"):
        sel.append(
            ChecklistSelection(
                checklist_id="SPIRIT-AI",
                role="primary" if design_type == "Prospective_Interventional_RCT" else "supporting",
                rationale="Prospective interventional component → SPIRIT-AI protocol items apply.",
            )
        )
        sel.append(
            ChecklistSelection(
                checklist_id="CONSORT-AI",
                role="supporting",
                rationale="Pre-plan the trial report against CONSORT-AI.",
            )
        )
    elif design_type in ("Standalone_Performance", "MRMC_Reader_Study"):
        sel.append(
            ChecklistSelection(
                checklist_id="SPIRIT-AI",
                role="supporting",
                rationale="Items 10(ii), 11a(i)–(vi), 22(ii) are good practice for the device description and error analysis even outside an RCT.",
            )
        )

    sel.append(
        ChecklistSelection(
            checklist_id="ISO14155-CIP",
            role="structural",
            rationale="ISO 14155:2020 Annex A defines the clinical investigation plan structure (adopted by TFDA GCP for devices).",
        )
    )
    sel.append(
        ChecklistSelection(
            checklist_id="IMDRF-N41",
            role="structural",
            rationale="State which SaMD clinical-evaluation pillar(s) the study provides.",
        )
    )
    if (
        any(x.startswith("US_FDA") or x == "FDA" for x in j)
        or design_type != "Prospective_Interventional_RCT"
    ):
        sel.append(
            ChecklistSelection(
                checklist_id="FDA-CADe",
                role="supporting",
                rationale="FDA CADe clinical performance assessment guidance is the de-facto template for standalone/MRMC designs.",
            )
        )
    if "TFDA" in j:
        sel.append(
            ChecklistSelection(
                checklist_id="TFDA-AIML-SaMD",
                role="primary",
                rationale="Taiwan registration: TFDA AI/ML SaMD technical guidance evidence elements.",
            )
        )
    # de-duplicate keeping first occurrence
    seen: set[str] = set()
    out: list[ChecklistSelection] = []
    for s in sel:
        if s.checklist_id not in seen:
            seen.add(s.checklist_id)
            out.append(s)
    return out


# ── coverage pre-screen ───────────────────────────────────────────────────────


class ItemCoverage(BaseModel):
    item_id: str
    section: str
    text: str
    status: Literal["likely_covered", "weak", "missing"]
    matched_keywords: list[str]
    matched_sections: list[str]


class CoverageReport(BaseModel):
    checklist_id: str
    n_items: int
    n_likely_covered: int
    n_weak: int
    n_missing: int
    items: list[ItemCoverage]
    note: str = (
        "Keyword pre-screen only: 'likely_covered' means the vocabulary is present, not that the "
        "item is adequately addressed. An LLM or human auditor must confirm each item."
    )


_CJK = re.compile(r"[一-鿿]")


def _keyword_hit(keyword: str, text_lower: str) -> bool:
    k = keyword.lower().strip()
    if not k:
        return False
    if _CJK.search(k):
        return k in text_lower
    # loose word-boundary match tolerant of hyphen/space variants
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(k).replace(r"\-", r"[-\s]?").replace(r"\ ", r"[-\s]?")
        + r"(?![a-z0-9])"
    )
    return re.search(pattern, text_lower) is not None


def prescreen_coverage(checklist_id: str, sections: dict[str, str]) -> CoverageReport:
    """Keyword-based pre-screen of draft protocol sections against a checklist."""
    cl = get_checklist(checklist_id)
    lowered = {name: (txt or "").lower() for name, txt in sections.items()}
    items: list[ItemCoverage] = []
    for it in cl.items:
        matched_kw: list[str] = []
        matched_sec: list[str] = []
        for kw in it.keywords:
            for sec_name, txt in lowered.items():
                if _keyword_hit(kw, txt):
                    if kw not in matched_kw:
                        matched_kw.append(kw)
                    if sec_name not in matched_sec:
                        matched_sec.append(sec_name)
        if len(matched_kw) >= 2:
            status: Literal["likely_covered", "weak", "missing"] = "likely_covered"
        elif len(matched_kw) == 1:
            status = "weak"
        else:
            status = "missing"
        items.append(
            ItemCoverage(
                item_id=it.id,
                section=it.section,
                text=it.text,
                status=status,
                matched_keywords=matched_kw,
                matched_sections=matched_sec,
            )
        )
    return CoverageReport(
        checklist_id=cl.id,
        n_items=len(items),
        n_likely_covered=sum(i.status == "likely_covered" for i in items),
        n_weak=sum(i.status == "weak" for i in items),
        n_missing=sum(i.status == "missing" for i in items),
        items=items,
    )
