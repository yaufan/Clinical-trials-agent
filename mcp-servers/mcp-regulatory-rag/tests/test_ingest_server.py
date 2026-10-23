import io

import pytest
from mcp.client.client import Client
from pypdf import PdfWriter

from mcp_regulatory_rag import ingest
from mcp_regulatory_rag import server as srv


def _make_pdf(path, pages):
    w = PdfWriter()
    for txt in pages:
        page = w.add_blank_page(width=612, height=792)
        # pypdf can't draw text easily; emulate extraction through a text annotation-free path:
        # we instead monkeypatch extract in the test below. Keep the PDF structural.
        _ = page, txt
    buf = io.BytesIO()
    w.write(buf)
    path.write_bytes(buf.getvalue())


def test_chunk_pages_tracks_headings_and_pages():
    pages = [
        ingest.PageText(
            page=1,
            text="1 Introduction\n"
            + ("Intro sentence about intended use. " * 20)
            + "\n\n2 Study Design\n"
            + ("Design detail. " * 30),
        ),
        ingest.PageText(page=2, text="第三章 參考標準\n" + ("參考標準由三位專科醫師建立。" * 25)),
    ]
    chunks = ingest.chunk_pages(pages, target_chars=400, overlap_chars=50, min_chars=50)
    assert len(chunks) >= 3
    headings = [h for _, _, h in chunks]
    assert "1 Introduction" in headings
    assert "2 Study Design" in headings
    assert any(h and h.startswith("第三章") for h in headings)
    assert any(p == 2 for _, p, _ in chunks)
    # overlap: a later chunk starts with the tail of the previous one when split mid-heading
    assert all(len(t) > 0 for t, _, _ in chunks)


def test_is_heading_patterns():
    assert ingest.is_heading("3.2 Reference Standard")
    assert ingest.is_heading("第五章 臨床效能驗證")
    assert ingest.is_heading("Appendix A")
    assert not ingest.is_heading("the reference standard should be established by")
    assert not ingest.is_heading("x" * 100)


def test_build_chunks_from_local_text_file(tmp_path):
    p = tmp_path / "guide.txt"
    p.write_text("1 Scope\n" + "This guidance applies to AI software. " * 40, encoding="utf-8")
    chunks = ingest.build_chunks_for_document(
        {"id": "local-1", "title": "Local", "path": str(p), "jurisdiction": "INTL"}, tmp_path
    )
    assert chunks and chunks[0].document_id == "local-1"
    assert chunks[0].heading == "1 Scope"


def test_build_chunks_from_pdf(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    _make_pdf(pdf, ["p1", "p2"])
    monkeypatch.setattr(
        ingest,
        "extract_pdf_pages",
        lambda path, max_pages=400: [
            ingest.PageText(page=1, text="1 Purpose\n" + "Purpose text. " * 30),
            ingest.PageText(page=2, text="2 Clinical Evaluation\n" + "Clinical text. " * 30),
        ],
    )
    chunks = ingest.build_chunks_for_document(
        {"id": "pdf-1", "title": "PDF", "path": str(pdf)}, tmp_path
    )
    assert {c.page for c in chunks} == {1, 2}


def test_checklist_chunks_cover_all_items():
    chunks = ingest.checklist_chunks()
    assert len(chunks) >= 80
    assert any("SPIRIT-AI 11a(i)" in c.text for c in chunks)


@pytest.mark.anyio
async def test_server_roundtrip(store):
    srv.set_store(store)
    try:
        async with Client(srv.server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            assert {
                "retrieve_guideline_clauses",
                "select_checklists",
                "prescreen_checklist_coverage",
                "get_checklist",
                "list_checklists",
                "list_indexed_documents",
            } <= names

            r = await client.call_tool(
                "retrieve_guideline_clauses",
                {"query": "washout reader study", "jurisdiction": "US", "top_k": 2},
            )
            assert not r.is_error
            assert r.structured_content["results"][0]["document_id"] == "fda-cade-2022"

            s = await client.call_tool(
                "select_checklists",
                {
                    "design_type": "MRMC_Reader_Study",
                    "samd_category": "CADe",
                    "jurisdictions": ["TFDA"],
                },
            )
            assert not s.is_error
            ids = [x["checklist_id"] for x in s.structured_content["result"]]
            assert ids[0] == "STARD-AI"

            c = await client.call_tool(
                "prescreen_checklist_coverage",
                {
                    "checklist_id": "STARD-AI",
                    "sections": {
                        "Design": "retrospective standalone study with a locked threshold"
                    },
                },
            )
            assert not c.is_error and c.structured_content["n_items"] == 15

            d = await client.call_tool("list_indexed_documents", {})
            assert d.structured_content["points"] == 4
    finally:
        srv.set_store(None)
