"""FDA "Artificial Intelligence-Enabled Medical Devices" list (CSV download).

The list is published as CSV/XLSX/XML on fda.gov; it is *not* an API and is updated a few
times a year. It covers 510(k), De Novo and PMA authorisations identified by AI-related terms
in their summaries, so it is a convenient seed for predicate searches by product code.
"""

from __future__ import annotations

import csv
import io
import re
import time
from datetime import date, datetime

import httpx
from pydantic import BaseModel, Field

from .pdfs import BROWSER_USER_AGENT, den_number_to_summary_url, k_number_to_summary_url

FDA_AI_LIST_CSV_URL = "https://www.fda.gov/media/178541/download?attachment"
_HEADER_HINTS = ("submission number", "device")


class AIDeviceRow(BaseModel):
    decision_date: date | None
    submission_number: str
    device_name: str
    company: str
    panel: str
    product_code: str
    submission_type: str = Field(description="510k | de_novo | pma | other")
    summary_url: str | None = None

    @classmethod
    def from_csv(cls, row: dict[str, str]) -> AIDeviceRow:
        sub = (row.get("submission_number") or "").strip().upper()
        if sub.startswith("K"):
            stype = "510k"
        elif sub.startswith("DEN"):
            stype = "de_novo"
        elif sub.startswith("P") or sub.startswith("H") or sub.startswith("N"):
            stype = "pma"
        else:
            stype = "other"
        url = None
        try:
            if stype == "510k":
                url = k_number_to_summary_url(sub)
            elif stype == "de_novo":
                url = den_number_to_summary_url(sub)
        except ValueError:
            url = None
        return cls(
            decision_date=_parse_date(row.get("decision_date", "")),
            submission_number=sub,
            device_name=(row.get("device_name") or "").strip(),
            company=(row.get("company") or "").strip(),
            panel=(row.get("panel") or "").strip(),
            product_code=(row.get("product_code") or "").strip().upper(),
            submission_type=stype,
            summary_url=url,
        )


def _parse_date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _canonical_header(name: str) -> str:
    n = re.sub(r"[^a-z]+", " ", name.lower()).strip()
    if "submission" in n:
        return "submission_number"
    if "date" in n:
        return "decision_date"
    if n.startswith("device"):
        return "device_name"
    if "company" in n or "applicant" in n or "manufacturer" in n:
        return "company"
    if "panel" in n:
        return "panel"
    if "product code" in n or "product" in n:
        return "product_code"
    return n.replace(" ", "_")


def parse_ai_device_csv(text: str) -> list[AIDeviceRow]:
    """Parse the FDA CSV, tolerating a title/preamble row before the real header."""
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    header_idx = None
    for i, r in enumerate(rows[:10]):
        lowered = " ".join(c.lower() for c in r)
        if all(h in lowered for h in _HEADER_HINTS):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(
            "could not locate the header row (expected 'Submission Number' and 'Device')"
        )
    headers = [_canonical_header(h) for h in rows[header_idx]]
    out: list[AIDeviceRow] = []
    for r in rows[header_idx + 1 :]:
        if not any(c.strip() for c in r):
            continue
        rec = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
        if not rec.get("submission_number"):
            continue
        out.append(AIDeviceRow.from_csv(rec))
    return out


class AIDeviceListCache:
    """Download-once cache with a TTL (the list changes a few times per year)."""

    def __init__(self, *, url: str = FDA_AI_LIST_CSV_URL, ttl_seconds: float = 6 * 3600) -> None:
        self.url = url
        self.ttl = ttl_seconds
        self._rows: list[AIDeviceRow] | None = None
        self._fetched_at: float = 0.0
        self.download_count = 0

    async def rows(
        self, *, client: httpx.AsyncClient | None = None, force: bool = False
    ) -> list[AIDeviceRow]:
        now = time.monotonic()
        if self._rows is not None and not force and now - self._fetched_at < self.ttl:
            return self._rows
        owns = client is None
        client = client or httpx.AsyncClient(timeout=90.0, follow_redirects=True)
        try:
            resp = await client.get(
                self.url, headers={"User-Agent": BROWSER_USER_AGENT, "Accept": "text/csv,*/*"}
            )
            resp.raise_for_status()
            text = resp.content.decode("utf-8-sig", errors="replace")
        finally:
            if owns:
                await client.aclose()
        self._rows = parse_ai_device_csv(text)
        self._fetched_at = now
        self.download_count += 1
        return self._rows


def filter_rows(
    rows: list[AIDeviceRow],
    *,
    keyword: str | None = None,
    product_code: str | None = None,
    panel: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    submission_type: str | None = None,
) -> list[AIDeviceRow]:
    out = rows
    if product_code:
        pc = product_code.strip().upper()
        out = [r for r in out if r.product_code == pc]
    if panel:
        p = panel.strip().lower()
        out = [r for r in out if p in r.panel.lower()]
    if submission_type:
        out = [r for r in out if r.submission_type == submission_type]
    if year_from:
        out = [r for r in out if r.decision_date and r.decision_date.year >= year_from]
    if year_to:
        out = [r for r in out if r.decision_date and r.decision_date.year <= year_to]
    if keyword:
        words = [w for w in re.split(r"\W+", keyword.lower()) if w]
        out = [r for r in out if all(w in f"{r.device_name} {r.company}".lower() for w in words)]
    return sorted(out, key=lambda r: r.decision_date or date.min, reverse=True)
