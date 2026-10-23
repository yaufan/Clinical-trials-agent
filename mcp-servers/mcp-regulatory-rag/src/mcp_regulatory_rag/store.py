"""Qdrant-backed hybrid (dense + BM25 sparse) guidance store."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models

from .embeddings import Embedder
from .tokenize import bm25_sparse

DENSE = "dense"
SPARSE = "bm25"
NAMESPACE = uuid.UUID("7c0d3a8e-8f3e-4f9b-9b7e-2a1c5f3d9e01")


class GuidanceChunk(BaseModel):
    document_id: str
    title: str
    jurisdiction: str = Field(description="TW | US | EU | INTL")
    doc_type: str = Field(description="guidance | standard | checklist | regulation | template")
    year: int | None = None
    source_url: str | None = None
    page: int | None = None
    chunk_index: int
    heading: str | None = None
    text: str
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def point_id(self) -> str:
        return str(uuid.uuid5(NAMESPACE, f"{self.document_id}:{self.chunk_index}"))


class RetrievedClause(BaseModel):
    score: float
    document_id: str
    title: str
    jurisdiction: str
    doc_type: str
    year: int | None
    page: int | None
    heading: str | None
    text: str
    source_url: str | None
    citation: str


class GuidanceStore:
    def __init__(
        self, client: QdrantClient, embedder: Embedder, collection: str = "regulatory_guidance"
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.collection = collection

    # ── lifecycle ────────────────────────────────────────────────────────────
    def ensure_collection(self, *, recreate: bool = False) -> None:
        exists = self.client.collection_exists(self.collection)
        if exists and recreate:
            self.client.delete_collection(self.collection)
            exists = False
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    DENSE: models.VectorParams(
                        size=self.embedder.dim, distance=models.Distance.COSINE
                    )
                },
                sparse_vectors_config={
                    SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )
            for field in ("document_id", "jurisdiction", "doc_type"):
                self.client.create_payload_index(
                    self.collection, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
                )

    # ── write ────────────────────────────────────────────────────────────────
    def upsert_chunks(self, chunks: list[GuidanceChunk], *, batch_size: int = 64) -> int:
        n = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            dense = self.embedder.embed([c.text for c in batch])
            points: list[models.PointStruct] = []
            for c, d in zip(batch, dense, strict=True):
                idx, vals = bm25_sparse(c.text)
                points.append(
                    models.PointStruct(
                        id=c.point_id,
                        vector={DENSE: d, SPARSE: models.SparseVector(indices=idx, values=vals)},
                        payload=c.model_dump(),
                    )
                )
            self.client.upsert(self.collection, points=points)
            n += len(points)
        return n

    def delete_document(self, document_id: str) -> None:
        self.client.delete(
            self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id", match=models.MatchValue(value=document_id)
                        )
                    ]
                )
            ),
        )

    # ── read ─────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        jurisdiction: str | None = None,
        document_id: str | None = None,
        doc_type: str | None = None,
    ) -> list[RetrievedClause]:
        must: list[models.Condition] = []
        if jurisdiction:
            must.append(
                models.FieldCondition(
                    key="jurisdiction", match=models.MatchValue(value=jurisdiction)
                )
            )
        if document_id:
            must.append(
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))
            )
        if doc_type:
            must.append(
                models.FieldCondition(key="doc_type", match=models.MatchValue(value=doc_type))
            )
        flt = models.Filter(must=must) if must else None

        dense_q = self.embedder.embed([query])[0]
        idx, vals = bm25_sparse(query)
        prefetch = [models.Prefetch(query=dense_q, using=DENSE, filter=flt, limit=top_k * 4)]
        if idx:
            prefetch.append(
                models.Prefetch(
                    query=models.SparseVector(indices=idx, values=vals),
                    using=SPARSE,
                    filter=flt,
                    limit=top_k * 4,
                )
            )
        res = self.client.query_points(
            self.collection,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )
        out: list[RetrievedClause] = []
        for p in res.points:
            pl = p.payload or {}
            cite = f"{pl.get('title')}"
            if pl.get("year"):
                cite += f" ({pl['year']})"
            if pl.get("heading"):
                cite += f", {pl['heading']}"
            if pl.get("page"):
                cite += f", p.{pl['page']}"
            out.append(
                RetrievedClause(
                    score=float(p.score),
                    document_id=pl.get("document_id", ""),
                    title=pl.get("title", ""),
                    jurisdiction=pl.get("jurisdiction", ""),
                    doc_type=pl.get("doc_type", ""),
                    year=pl.get("year"),
                    page=pl.get("page"),
                    heading=pl.get("heading"),
                    text=pl.get("text", ""),
                    source_url=pl.get("source_url"),
                    citation=cite,
                )
            )
        return out

    def list_documents(self) -> list[dict[str, Any]]:
        docs: dict[str, dict[str, Any]] = {}
        offset = None
        while True:
            points, offset = self.client.scroll(
                self.collection,
                limit=256,
                offset=offset,
                with_payload=[
                    "document_id",
                    "title",
                    "jurisdiction",
                    "doc_type",
                    "year",
                    "source_url",
                ],
                with_vectors=False,
            )
            for p in points:
                pl = p.payload or {}
                d = docs.setdefault(
                    pl.get("document_id", "?"),
                    {
                        "document_id": pl.get("document_id"),
                        "title": pl.get("title"),
                        "jurisdiction": pl.get("jurisdiction"),
                        "doc_type": pl.get("doc_type"),
                        "year": pl.get("year"),
                        "source_url": pl.get("source_url"),
                        "chunks": 0,
                    },
                )
                d["chunks"] += 1
            if offset is None:
                break
        return sorted(
            docs.values(), key=lambda d: (d.get("jurisdiction") or "", d.get("document_id") or "")
        )

    def count(self) -> int:
        return int(self.client.count(self.collection, exact=True).count)
