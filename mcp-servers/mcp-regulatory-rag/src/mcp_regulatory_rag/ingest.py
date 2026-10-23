"""Corpus ingestion: download → extract → chunk → embed → upsert.

python -m mcp_regulatory_rag.ingest --sources sources.yaml [--recreate] [--include-checklists]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml
from pypdf import PdfReader

from .checklists import load_all
from .embeddings import embedder_from_env
from .store import GuidanceChunk, GuidanceStore

log = logging.getLogger("mcp_regulatory_rag.ingest")

UA = "Mozilla/5.0 (X11; Linux aarch64) ai-samd-protocol-copilot/0.1 (+regulatory-rag ingest)"

_HEADING_PATTERNS = [
    re.compile(r"^\s*(\d+(?:\.\d+){0,3})\s+[A-Z一-鿿][^\n]{2,80}$"),
    re.compile(r"^\s*第[一二三四五六七八九十百\d]+[章節條項款][^\n]{0,60}$"),
    re.compile(
        r"^\s*([一二三四五六七八九十]+|[（(][一二三四五六七八九十\d]+[）)])[、.．][^\n]{1,60}$"
    ),
    re.compile(
        r"^\s*(附錄|附件|Annex|Appendix|Section|Part)\s*[A-Z\d一二三四五六七八九十]*[^\n]{0,60}$",
        re.I,
    ),
    re.compile(r"^\s*[A-Z][A-Z0-9 ,&/\-()]{6,80}$"),
]


@dataclass
class PageText:
    page: int
    text: str


def is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 90:
        return False
    return any(p.match(line) for p in _HEADING_PATTERNS)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf_pages(path: Path, max_pages: int = 400) -> list[PageText]:
    reader = PdfReader(str(path))
    pages: list[PageText] = []
    for i, page in enumerate(reader.pages[:max_pages], start=1):
        try:
            txt = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - corrupt page
            log.warning("page %s extraction failed: %s", i, exc)
            txt = ""
        pages.append(PageText(page=i, text=clean_text(txt)))
    return pages


def extract_text_file(path: Path) -> list[PageText]:
    return [PageText(page=1, text=clean_text(path.read_text(encoding="utf-8", errors="replace")))]


def chunk_pages(
    pages: list[PageText],
    *,
    target_chars: int = 900,
    overlap_chars: int = 150,
    min_chars: int = 200,
) -> list[tuple[str, int | None, str | None]]:
    """Heading-aware sliding chunker → list of (text, page, heading)."""
    chunks: list[tuple[str, int | None, str | None]] = []
    buf: list[str] = []
    buf_len = 0
    buf_page: int | None = None
    heading: str | None = None

    def flush() -> None:
        nonlocal buf, buf_len, buf_page
        if buf_len >= min_chars or (buf and not chunks):
            text = "\n".join(buf).strip()
            if text:
                chunks.append((text, buf_page, heading))
        buf, buf_len, buf_page = [], 0, None

    for pg in pages:
        for para in re.split(
            r"\n\s*\n|\n(?=\s*(?:\d+(?:\.\d+)*\s|第[一二三四五六七八九十百\d]+[章節條]))", pg.text
        ):
            para = para.strip()
            if not para:
                continue
            first_line = para.splitlines()[0]
            if is_heading(first_line):
                flush()
                heading = first_line.strip()
            if buf_len + len(para) > target_chars and buf:
                flush()
                # overlap: carry the tail of the previous chunk
                if chunks:
                    tail = chunks[-1][0][-overlap_chars:]
                    buf, buf_len, buf_page = [tail], len(tail), pg.page
            if buf_page is None:
                buf_page = pg.page
            buf.append(para)
            buf_len += len(para)
    flush()
    return chunks


def download(url: str, dest: Path, *, client: httpx.Client | None = None) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    own = client is None
    client = client or httpx.Client(
        follow_redirects=True, timeout=120.0, headers={"User-Agent": UA}
    )
    try:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with dest.open("wb") as fh:
                for part in resp.iter_bytes():
                    fh.write(part)
    finally:
        if own:
            client.close()
    return dest


def checklist_chunks() -> list[GuidanceChunk]:
    out: list[GuidanceChunk] = []
    for cl in load_all().values():
        for i, item in enumerate(cl.items):
            out.append(
                GuidanceChunk(
                    document_id=f"checklist:{cl.id}",
                    title=cl.title,
                    jurisdiction="TW"
                    if cl.id.startswith("TFDA")
                    else ("US" if cl.id.startswith("FDA") else "INTL"),
                    doc_type="checklist",
                    year=None,
                    source_url=None,
                    page=None,
                    chunk_index=i,
                    heading=f"{cl.id} item {item.id} — {item.section}",
                    text=f"{cl.id} {item.id} ({item.section}; {item.type}): {item.text}\nKeywords: {', '.join(item.keywords)}",
                    extra={"checklist_id": cl.id, "item_id": item.id},
                )
            )
    return out


def build_chunks_for_document(
    doc: dict, data_dir: Path, *, client: httpx.Client | None = None
) -> list[GuidanceChunk]:
    doc_id = doc["id"]
    if doc.get("path"):
        src = Path(doc["path"])
        if not src.is_absolute():
            src = Path.cwd() / src
    else:
        url = doc["url"]
        ext = (
            ".pdf"
            if ".pdf" in url.lower() or "download" in url.lower() or "GetFile" in url
            else ".bin"
        )
        name = f"{doc_id}-{hashlib.sha1(url.encode()).hexdigest()[:8]}{ext}"
        src = download(url, data_dir / name, client=client)
    if not src.exists():
        raise FileNotFoundError(src)
    head = src.open("rb").read(5)
    if head.startswith(b"%PDF") or src.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(src)
    else:
        pages = extract_text_file(src)
    chunks = chunk_pages(pages)
    return [
        GuidanceChunk(
            document_id=doc_id,
            title=doc["title"],
            jurisdiction=doc.get("jurisdiction", "INTL"),
            doc_type=doc.get("doc_type", "guidance"),
            year=doc.get("year"),
            source_url=doc.get("url"),
            page=page,
            chunk_index=i,
            heading=heading,
            text=text,
            extra={"notes": doc.get("notes")} if doc.get("notes") else {},
        )
        for i, (text, page, heading) in enumerate(chunks)
    ]


def make_store(qdrant_url: str | None, collection: str) -> GuidanceStore:
    from qdrant_client import QdrantClient

    if not qdrant_url:
        client = QdrantClient(path=os.environ.get("QDRANT_LOCAL_PATH", "data/qdrant_local"))
    elif qdrant_url == ":memory:":
        client = QdrantClient(":memory:")
    else:
        client = QdrantClient(url=qdrant_url, api_key=os.environ.get("QDRANT_API_KEY") or None)
    return GuidanceStore(client, embedder_from_env(dict(os.environ)), collection)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(prog="mcp-regulatory-rag-ingest")
    ap.add_argument("--sources", default="sources.yaml")
    ap.add_argument("--data-dir", default="data/corpus")
    ap.add_argument("--qdrant-url", default=os.environ.get("QDRANT_URL"))
    ap.add_argument(
        "--collection", default=os.environ.get("QDRANT_COLLECTION", "regulatory_guidance")
    )
    ap.add_argument("--recreate", action="store_true", help="drop and recreate the collection")
    ap.add_argument(
        "--include-checklists", action="store_true", help="also index the YAML checklist items"
    )
    ap.add_argument("--only", nargs="*", help="document ids to (re)ingest")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(Path(args.sources).read_text(encoding="utf-8"))
    store = make_store(args.qdrant_url, args.collection)
    store.ensure_collection(recreate=args.recreate)
    log.info("embedder: %s (dim=%s)", store.embedder.name, store.embedder.dim)

    total = 0
    with httpx.Client(follow_redirects=True, timeout=180.0, headers={"User-Agent": UA}) as client:
        for doc in cfg.get("documents", []):
            if args.only and doc["id"] not in args.only:
                continue
            try:
                chunks = build_chunks_for_document(doc, Path(args.data_dir), client=client)
            except Exception as exc:
                log.error("skipping %s: %s", doc["id"], exc)
                continue
            store.delete_document(doc["id"])
            n = store.upsert_chunks(chunks)
            total += n
            log.info("indexed %s: %d chunks", doc["id"], n)
    if args.include_checklists:
        chunks = checklist_chunks()
        for cid in {c.document_id for c in chunks}:
            store.delete_document(cid)
        n = store.upsert_chunks(chunks)
        total += n
        log.info("indexed checklists: %d items", n)
    log.info("done; %d chunks written, collection now holds %d points", total, store.count())
    return 0


if __name__ == "__main__":
    sys.exit(main())
