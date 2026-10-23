"""Thin async client for the ClinicalTrials.gov API v2 (https://clinicaltrials.gov/data-api/api)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://clinicaltrials.gov/api/v2"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class CTGovError(RuntimeError):
    """Raised when the API returns a non-retryable error or retries are exhausted."""


class CTGovClient:
    """Async wrapper with bounded retries.

    ``base_url`` and ``transport`` are injectable so tests can point at a mock.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
        user_agent: str = "ai-samd-protocol-copilot/0.1 (mcp-clinicaltrials)",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CTGovClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ── low level ────────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        attempt = 0
        last_error: str | None = None
        while attempt <= self.max_retries:
            try:
                resp = await self._client.get(path, params=params)
            except httpx.TransportError as exc:  # network hiccup → retry
                last_error = f"transport error: {exc}"
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    raise CTGovError(f"not found: {path}")
                if resp.status_code not in RETRY_STATUSES:
                    raise CTGovError(f"HTTP {resp.status_code} for {path}: {resp.text[:300]}")
                last_error = f"HTTP {resp.status_code}"
            attempt += 1
            if attempt <= self.max_retries:
                await asyncio.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
        raise CTGovError(f"giving up on {path} after {self.max_retries} retries ({last_error})")

    # ── endpoints ────────────────────────────────────────────────────────────

    async def search_studies(
        self,
        *,
        query_cond: str | None = None,
        query_intr: str | None = None,
        query_term: str | None = None,
        study_type: str | None = None,
        status: list[str] | None = None,
        page_size: int = 20,
        page_token: str | None = None,
        fields: list[str] | None = None,
        count_total: bool = True,
    ) -> dict[str, Any]:
        """GET /studies. ``study_type`` is INTERVENTIONAL / OBSERVATIONAL / EXPANDED_ACCESS."""
        params: dict[str, Any] = {"format": "json", "pageSize": max(1, min(page_size, 1000))}
        if query_cond:
            params["query.cond"] = query_cond
        if query_intr:
            params["query.intr"] = query_intr
        if query_term:
            params["query.term"] = query_term
        if study_type:
            params["filter.advanced"] = f"AREA[StudyType]{study_type.upper()}"
        if status:
            params["filter.overallStatus"] = ",".join(s.upper() for s in status)
        if page_token:
            params["pageToken"] = page_token
        if fields:
            params["fields"] = ",".join(fields)
        if count_total:
            params["countTotal"] = "true"
        return await self._get("/studies", params)

    async def get_study(self, nct_id: str) -> dict[str, Any]:
        """GET /studies/{nctId}."""
        nct = nct_id.strip().upper()
        if not nct.startswith("NCT") or not nct[3:].isdigit():
            raise CTGovError(f"invalid NCT id: {nct_id!r}")
        return await self._get(f"/studies/{nct}", {"format": "json"})
