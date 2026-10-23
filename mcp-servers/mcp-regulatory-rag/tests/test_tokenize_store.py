import pytest

from mcp_regulatory_rag.embeddings import HashingEmbedder, cosine
from mcp_regulatory_rag.tokenize import bm25_sparse, token_id, tokenize


def test_tokenize_bilingual():
    toks = tokenize(
        "The MRMC reader-study used a 4-week washout. 參考標準由三位神經放射科醫師建立。"
    )
    assert "mrmc" in toks and "washout" in toks
    assert "the" not in toks
    assert any("參考" in t or "標準" in t for t in toks)
    assert any("醫師" in t for t in toks)


def test_bm25_sparse_is_deterministic_and_saturates():
    i1, v1 = bm25_sparse("sensitivity sensitivity sensitivity specificity")
    i2, v2 = bm25_sparse("sensitivity sensitivity sensitivity specificity")
    assert i1 == i2 and v1 == v2
    d = dict(zip(i1, v1, strict=True))
    assert d[token_id("sensitivity")] > d[token_id("specificity")]
    assert d[token_id("sensitivity")] < 2.2  # k1+1 upper bound


def test_hashing_embedder_similarity_is_meaningful():
    emb = HashingEmbedder(dim=128)
    a, b, c = emb.embed(
        [
            "reader study washout period",
            "washout period in reader studies",
            "pathology reference standard",
        ]
    )
    assert cosine(a, b) > cosine(a, c)
    assert len(a) == 128


def test_store_hybrid_search_english(store):
    res = store.search("washout period between reading sessions MRMC", top_k=2)
    assert res and res[0].document_id == "fda-cade-2022"
    assert res[0].heading == "Reader Study Design"
    assert "p.9" in res[0].citation


def test_store_hybrid_search_chinese(store):
    res = store.search("次族群 影像設備廠牌 效能", top_k=2)
    assert res and res[0].document_id == "tfda-aiml-samd-2020"
    assert res[0].page == 14


def test_store_filter_by_jurisdiction(store):
    res = store.search("reference standard 參考標準", top_k=3, jurisdiction="TW")
    assert res and all(r.jurisdiction == "TW" for r in res)


def test_store_list_and_delete(store):
    docs = store.list_documents()
    assert {d["document_id"] for d in docs} == {"tfda-aiml-samd-2020", "fda-cade-2022"}
    assert sum(d["chunks"] for d in docs) == 4
    store.delete_document("fda-cade-2022")
    assert store.count() == 2


@pytest.mark.parametrize("dim", [16, 64])
def test_ensure_collection_idempotent(dim):
    from qdrant_client import QdrantClient

    from mcp_regulatory_rag.store import GuidanceStore

    s = GuidanceStore(QdrantClient(":memory:"), HashingEmbedder(dim=dim), "c")
    s.ensure_collection()
    s.ensure_collection()
    assert s.count() == 0
