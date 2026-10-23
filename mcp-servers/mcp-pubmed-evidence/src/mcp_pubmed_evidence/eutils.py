"""Async NCBI E-utilities client (esearch / esummary / efetch) for PubMed.

Documented API: https://www.ncbi.nlm.nih.gov/books/NBK25499/
Policy: ≤3 requests/s without an API key, ≤10 requests/s with one; always send ``tool`` and
``email`` so NCBI can contact the operator before blocking.
"""

from __future__ import annotations

import asyncio
import os
import xml.etree.ElementTree as ET
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .models import ESearchResult, PubMedArticle
from .ratelimit import TokenBucket

DEFAULT_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class EUtilsError(RuntimeError):
    """Raised when NCBI returns an error payload or exhausts retries."""


class EUtilsClient:
    """Thin async wrapper around the three E-utilities endpoints PubMed evidence needs."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        tool: str | None = None,
        email: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limiter: TokenBucket | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.api_key = api_key if api_key is not None else os.environ.get("NCBI_API_KEY") or None
        self.tool = tool or os.environ.get("NCBI_TOOL", "ai-samd-protocol-copilot")
        self.email = email if email is not None else os.environ.get("NCBI_EMAIL") or None
        self._own_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self.max_retries = max_retries
        self._sleep = sleep
        rate = 10.0 if self.api_key else 3.0
        self._bucket = rate_limiter or TokenBucket(rate=rate, capacity=int(rate))

    async def aclose(self) -> None:
        if self._own_client:
            await self._http.aclose()

    async def __aenter__(self) -> EUtilsClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ── low level ────────────────────────────────────────────────────────────

    def _common_params(self) -> dict[str, str]:
        params = {"db": "pubmed", "tool": self.tool}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    async def _get(self, endpoint: str, params: dict[str, Any]) -> httpx.Response:
        url = self.base_url + endpoint
        merged = {**self._common_params(), **{k: v for k, v in params.items() if v is not None}}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self._bucket.acquire()
            try:
                resp = await self._http.get(url, params=merged)
            except httpx.TransportError as exc:  # network blip → retry
                last_exc = exc
            else:
                if resp.status_code not in RETRY_STATUSES:
                    resp.raise_for_status()
                    return resp
                last_exc = httpx.HTTPStatusError(
                    f"NCBI returned {resp.status_code}", request=resp.request, response=resp
                )
            if attempt < self.max_retries:
                await self._sleep(min(2.0**attempt, 8.0))
        raise EUtilsError(f"E-utilities request to {endpoint} failed after retries") from last_exc

    # ── endpoints ────────────────────────────────────────────────────────────

    async def esearch(
        self,
        term: str,
        *,
        retmax: int = 20,
        retstart: int = 0,
        sort: str = "relevance",
        use_history: bool = False,
        mindate: str | None = None,
        maxdate: str | None = None,
    ) -> ESearchResult:
        params: dict[str, Any] = {
            "term": term,
            "retmax": retmax,
            "retstart": retstart,
            "retmode": "json",
            "sort": sort,
        }
        if use_history:
            params["usehistory"] = "y"
        if mindate or maxdate:
            params["datetype"] = "pdat"
            params["mindate"] = mindate
            params["maxdate"] = maxdate
        resp = await self._get("esearch.fcgi", params)
        data = resp.json()
        if "esearchresult" not in data:
            raise EUtilsError(f"unexpected esearch payload: {str(data)[:200]}")
        res = data["esearchresult"]
        if "ERROR" in res:
            raise EUtilsError(f"esearch error: {res['ERROR']}")
        return ESearchResult(
            query=term,
            count=int(res.get("count", 0)),
            pmids=[str(x) for x in res.get("idlist", [])],
            retmax=int(res.get("retmax", retmax)),
            retstart=int(res.get("retstart", retstart)),
            webenv=res.get("webenv"),
            query_key=res.get("querykey"),
            query_translation=res.get("querytranslation"),
        )

    async def esummary(self, pmids: list[str]) -> list[PubMedArticle]:
        """Lightweight bibliographic records (no abstract)."""
        if not pmids:
            return []
        resp = await self._get("esummary.fcgi", {"id": ",".join(pmids), "retmode": "json"})
        data = resp.json().get("result", {})
        articles: list[PubMedArticle] = []
        for uid in data.get("uids", []):
            rec = data.get(uid, {})
            if "error" in rec:
                continue
            doi = pmc = None
            for aid in rec.get("articleids", []):
                if aid.get("idtype") == "doi":
                    doi = aid.get("value")
                elif aid.get("idtype") == "pmc":
                    pmc = aid.get("value")
            if doi is None and rec.get("elocationid", "").startswith("doi:"):
                doi = rec["elocationid"].removeprefix("doi:").strip()
            articles.append(
                PubMedArticle(
                    pmid=str(uid),
                    title=_strip_dot(rec.get("title", "")),
                    journal=rec.get("fulljournalname", "") or rec.get("source", ""),
                    journal_abbreviation=rec.get("source", ""),
                    year=_year_from_text(rec.get("pubdate", "")),
                    volume=rec.get("volume", ""),
                    issue=rec.get("issue", ""),
                    pages=rec.get("pages", ""),
                    authors=[a.get("name", "") for a in rec.get("authors", []) if a.get("name")],
                    doi=doi,
                    pmc_id=pmc,
                    publication_types=list(rec.get("pubtype", [])),
                )
            )
        return articles

    async def efetch_abstracts(self, pmids: list[str]) -> list[PubMedArticle]:
        """Full records including abstract and MeSH terms (XML)."""
        if not pmids:
            return []
        resp = await self._get(
            "efetch.fcgi", {"id": ",".join(pmids), "retmode": "xml", "rettype": "abstract"}
        )
        return parse_pubmed_xml(resp.text)

    async def search_and_fetch(
        self,
        term: str,
        *,
        retmax: int = 20,
        sort: str = "relevance",
    ) -> tuple[ESearchResult, list[PubMedArticle]]:
        search = await self.esearch(term, retmax=retmax, sort=sort)
        articles = await self.efetch_abstracts(search.pmids)
        return search, articles


# ─────────────────────────────────────────────────────────────────────────────
# XML parsing
# ─────────────────────────────────────────────────────────────────────────────


def _strip_dot(text: str) -> str:
    return text.strip().rstrip(".").strip()


def _year_from_text(text: str) -> int | None:
    for token in text.replace("-", " ").split():
        if token.isdigit() and len(token) == 4:
            return int(token)
    return None


def _text(elem: ET.Element | None) -> str:
    """Concatenate all text inside an element (handles inline <i>, <sup> etc.)."""
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def parse_pubmed_xml(xml_text: str) -> list[PubMedArticle]:
    """Parse an efetch ``PubmedArticleSet`` document into :class:`PubMedArticle` objects."""
    root = ET.fromstring(xml_text)
    out: list[PubMedArticle] = []
    for pa in root.iter("PubmedArticle"):
        citation = pa.find("MedlineCitation")
        if citation is None:
            continue
        pmid = _text(citation.find("PMID"))
        article = citation.find("Article")
        if article is None:
            continue
        title = _strip_dot(_text(article.find("ArticleTitle")))

        # abstract sections
        parts: list[str] = []
        abstract = article.find("Abstract")
        if abstract is not None:
            for at in abstract.findall("AbstractText"):
                label = at.get("Label") or at.get("NlmCategory")
                txt = _text(at)
                if not txt:
                    continue
                parts.append(f"{label.strip().upper()}: {txt}" if label else txt)
        abstract_text = "\n".join(parts)

        journal = article.find("Journal")
        journal_title = _text(journal.find("Title")) if journal is not None else ""
        journal_abbr = _text(journal.find("ISOAbbreviation")) if journal is not None else ""
        volume = issue = ""
        year: int | None = None
        if journal is not None:
            ji = journal.find("JournalIssue")
            if ji is not None:
                volume = _text(ji.find("Volume"))
                issue = _text(ji.find("Issue"))
                pubdate = ji.find("PubDate")
                if pubdate is not None:
                    y = _text(pubdate.find("Year"))
                    if y.isdigit():
                        year = int(y)
                    else:
                        year = _year_from_text(_text(pubdate.find("MedlineDate")))
        if year is None:
            # fall back to ArticleDate
            ad = article.find("ArticleDate")
            if ad is not None and _text(ad.find("Year")).isdigit():
                year = int(_text(ad.find("Year")))

        pages = ""
        pagination = article.find("Pagination")
        if pagination is not None:
            pages = _text(pagination.find("MedlinePgn"))

        authors: list[str] = []
        al = article.find("AuthorList")
        if al is not None:
            for au in al.findall("Author"):
                last = _text(au.find("LastName"))
                initials = _text(au.find("Initials"))
                collective = _text(au.find("CollectiveName"))
                if last:
                    authors.append(f"{last} {initials}".strip())
                elif collective:
                    authors.append(collective)

        doi = pmc = None
        for eloc in article.findall("ELocationID"):
            if eloc.get("EIdType") == "doi" and _text(eloc):
                doi = _text(eloc)
        pubmed_data = pa.find("PubmedData")
        if pubmed_data is not None:
            for aid in pubmed_data.findall("./ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi" and not doi:
                    doi = _text(aid)
                elif aid.get("IdType") == "pmc":
                    pmc = _text(aid)

        mesh = [
            _text(mh.find("DescriptorName"))
            for mh in citation.findall("./MeshHeadingList/MeshHeading")
            if _text(mh.find("DescriptorName"))
        ]
        pub_types = [
            _text(pt)
            for pt in article.findall("./PublicationTypeList/PublicationType")
            if _text(pt)
        ]

        out.append(
            PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract_text,
                journal=journal_title,
                journal_abbreviation=journal_abbr,
                year=year,
                volume=volume,
                issue=issue,
                pages=pages,
                authors=authors,
                doi=doi,
                pmc_id=pmc,
                mesh_terms=mesh,
                publication_types=pub_types,
            )
        )
    return out
