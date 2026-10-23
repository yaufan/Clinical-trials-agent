"""Async client for the openFDA device/510k endpoint.

openFDA quirks handled here:

* A query with no matches returns HTTP 404 with ``{"error": {"code": "NOT_FOUND"}}`` — this
  is *not* an error for our purposes and yields an empty result set.
* Multi-word keywords must be written as ``field:(word1+word2)``; quoted phrases are not
  reliably matched. Spaces inside parentheses act as the term separator.
* Date ranges use ``field:[YYYY-MM-DD+TO+YYYY-MM-DD]``.
* Rate limits: 40 requests/min without an API key, 240/min with ``api_key``.
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

OPENFDA_BASE_URL = "https://api.fda.gov"
USER_AGENT = "ai-samd-protocol-copilot/0.1 (mcp-openfda-predicate)"
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")


class OpenFDAMeta(BaseModel):
    skip: int = 0
    limit: int = 0
    total: int = 0
    last_updated: str | None = None


class Device510k(BaseModel):
    """One openFDA 510(k) record, trimmed to the fields useful for predicate research."""

    k_number: str
    device_name: str = ""
    applicant: str = ""
    decision_date: str = ""
    date_received: str = ""
    decision_code: str = ""
    decision_description: str = ""
    product_code: str = ""
    clearance_type: str = ""
    advisory_committee: str = ""
    advisory_committee_description: str = ""
    statement_or_summary: str = Field(
        default="", description="'Summary' when a 510(k) summary exists"
    )
    device_class: str | None = None
    regulation_number: str | None = None
    generic_device_name: str | None = Field(default=None, description="openFDA classification name")
    medical_specialty: str | None = None
    summary_pdf_url: str | None = None

    @classmethod
    def from_openfda(cls, rec: dict[str, Any]) -> Device510k:
        of = rec.get("openfda") or {}
        from .pdfs import k_number_to_summary_url

        k = str(rec.get("k_number", "")).strip()
        return cls(
            k_number=k,
            device_name=rec.get("device_name", "") or "",
            applicant=rec.get("applicant", "") or "",
            decision_date=rec.get("decision_date", "") or "",
            date_received=rec.get("date_received", "") or "",
            decision_code=rec.get("decision_code", "") or "",
            decision_description=rec.get("decision_description", "") or "",
            product_code=rec.get("product_code", "") or "",
            clearance_type=rec.get("clearance_type", "") or "",
            advisory_committee=rec.get("advisory_committee", "") or "",
            advisory_committee_description=rec.get("advisory_committee_description", "") or "",
            statement_or_summary=rec.get("statement_or_summary", "") or "",
            device_class=_first(of.get("device_class")),
            regulation_number=_first(of.get("regulation_number")),
            generic_device_name=_first(of.get("device_name")),
            medical_specialty=_first(of.get("medical_specialty_description")),
            summary_pdf_url=k_number_to_summary_url(k) if k else None,
        )


class Search510kResult(BaseModel):
    query: str
    meta: OpenFDAMeta
    devices: list[Device510k]


def _first(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value)


def keyword_clause(field: str, keyword: str) -> str:
    """``device_name:(computer aided)`` → ``device_name:(computer+aided)``."""
    tokens = _TOKEN_RE.findall(keyword)
    if not tokens:
        raise ValueError("keyword contains no searchable tokens")
    if len(tokens) == 1:
        return f"{field}:{tokens[0]}"
    return f"{field}:({'+'.join(tokens)})"


def date_range_clause(field: str, start: str | None, end: str | None) -> str | None:
    if not start and not end:
        return None
    for v in (start, end):
        if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError(f"dates must be YYYY-MM-DD; got {v!r}")
    return f"{field}:[{start or '1976-01-01'}+TO+{end or '2099-12-31'}]"


def build_510k_query(
    *,
    product_code: str | None = None,
    keyword: str | None = None,
    applicant: str | None = None,
    decision_date_from: str | None = None,
    decision_date_to: str | None = None,
    k_number: str | None = None,
) -> str:
    clauses: list[str] = []
    if k_number:
        clauses.append(f"k_number:{k_number.strip().upper()}")
    if product_code:
        clauses.append(f"product_code:{product_code.strip().upper()}")
    if keyword:
        clauses.append(keyword_clause("device_name", keyword))
    if applicant:
        clauses.append(keyword_clause("applicant", applicant))
    dr = date_range_clause("decision_date", decision_date_from, decision_date_to)
    if dr:
        clauses.append(dr)
    if not clauses:
        raise ValueError("at least one search criterion is required")
    return "+AND+".join(clauses)


class OpenFDAClient:
    def __init__(
        self,
        *,
        base_url: str = OPENFDA_BASE_URL,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("OPENFDA_API_KEY") or None
        self._client = client
        self._owns_client = client is None
        self._timeout = timeout
        self.max_retries = max_retries

    async def __aenter__(self) -> OpenFDAClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout, headers={"User-Agent": USER_AGENT}
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout, headers={"User-Agent": USER_AGENT}
            )
        return self._client

    async def _get(self, path: str, query: str, limit: int, skip: int) -> dict[str, Any] | None:
        """GET with the raw ``search`` string; returns None when openFDA reports no matches."""
        # openFDA's Lucene syntax relies on literal '+' and ':' — build the URL by hand so httpx
        # does not percent-encode them.
        params = f"search={query}&limit={int(limit)}&skip={int(skip)}"
        if self.api_key:
            params += f"&api_key={self.api_key}"
        url = f"{self.base_url}{path}?{params}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await self.client.get(url)
            except httpx.TransportError as exc:  # network blip → retry
                last_exc = exc
                await asyncio.sleep(min(2**attempt, 8) * 0.25)
                continue
            if resp.status_code == 404:
                try:
                    body = resp.json()
                except ValueError:
                    body = {}
                if (body.get("error") or {}).get("code") == "NOT_FOUND":
                    return None
                resp.raise_for_status()
            if resp.status_code in _RETRY_STATUSES and attempt < self.max_retries:
                retry_after = resp.headers.get("retry-after")
                delay = (
                    float(retry_after)
                    if retry_after and retry_after.isdigit()
                    else min(2**attempt, 8) * 0.25
                )
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.json()
        if last_exc:
            raise last_exc
        raise httpx.HTTPError("openFDA request failed after retries")

    async def search_510k(self, query: str, *, limit: int = 20, skip: int = 0) -> Search510kResult:
        limit = max(1, min(int(limit), 100))
        data = await self._get("/device/510k.json", query, limit, skip)
        if data is None:
            return Search510kResult(
                query=query, meta=OpenFDAMeta(skip=skip, limit=limit, total=0), devices=[]
            )
        meta_raw = data.get("meta", {})
        results_meta = meta_raw.get("results", {})
        meta = OpenFDAMeta(
            skip=int(results_meta.get("skip", skip)),
            limit=int(results_meta.get("limit", limit)),
            total=int(results_meta.get("total", 0)),
            last_updated=meta_raw.get("last_updated"),
        )
        devices = [Device510k.from_openfda(r) for r in data.get("results", [])]
        return Search510kResult(query=query, meta=meta, devices=devices)

    async def get_510k(self, k_number: str) -> Device510k | None:
        res = await self.search_510k(build_510k_query(k_number=k_number), limit=1)
        return res.devices[0] if res.devices else None
