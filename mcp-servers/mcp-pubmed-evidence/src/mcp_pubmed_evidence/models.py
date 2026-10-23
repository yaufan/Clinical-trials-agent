"""Pydantic models shared by the E-utilities client, extractor and MCP tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PubMedArticle(BaseModel):
    pmid: str
    title: str = ""
    abstract: str = Field(default="", description="Labelled sections joined as 'LABEL: text'")
    journal: str = ""
    journal_abbreviation: str = ""
    year: int | None = None
    volume: str = ""
    issue: str = ""
    pages: str = ""
    authors: list[str] = Field(default_factory=list, description="'Last FM' strings")
    doi: str | None = None
    pmc_id: str | None = None
    mesh_terms: list[str] = Field(default_factory=list)
    publication_types: list[str] = Field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"


class ESearchResult(BaseModel):
    query: str
    count: int
    pmids: list[str]
    retmax: int
    retstart: int
    webenv: str | None = None
    query_key: str | None = None
    query_translation: str | None = None


MetricName = Literal[
    "sensitivity",
    "specificity",
    "auc",
    "accuracy",
    "ppv",
    "npv",
    "f1",
    "dice",
]


class MetricMention(BaseModel):
    metric: MetricName
    value: float = Field(description="Proportion on the 0–1 scale")
    ci_low: float | None = None
    ci_high: float | None = None
    as_reported: str = Field(description="The raw matched text")
    context: str = Field(description="Surrounding snippet from the abstract")


class SampleSizeMention(BaseModel):
    n: int
    unit: str = Field(description="patients / cases / images / scans / lesions / n")
    context: str


class PerformanceExtract(BaseModel):
    metrics: list[MetricMention] = Field(default_factory=list)
    sample_sizes: list[SampleSizeMention] = Field(default_factory=list)
    reader_count: int | None = Field(
        default=None, description="Number of readers/radiologists if stated"
    )
    design_keywords: list[str] = Field(default_factory=list)
    has_ai_terms: bool = Field(
        default=False, description="True if the text mentions AI/ML/deep learning"
    )


class ArticleWithEvidence(BaseModel):
    article: PubMedArticle
    extract: PerformanceExtract
    citation: str
    url: str


class SearchResponse(BaseModel):
    query: str = Field(description="Exact PubMed term string sent to esearch")
    query_translation: str | None = Field(
        default=None, description="NCBI's translation of the query"
    )
    total_count: int
    returned: int
    articles: list[ArticleWithEvidence]
    notes: list[str] = Field(default_factory=list)


class CitationsResponse(BaseModel):
    style: Literal["vancouver", "apa"]
    articles: list[PubMedArticle]
    citations: list[str]
    missing_pmids: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    query: str
    components: dict[str, str] = Field(description="Named clauses that were AND-ed together")
    purpose: Literal["baseline_unaided", "ai_evidence"]
