import pytest
from qdrant_client import QdrantClient

from mcp_regulatory_rag.embeddings import HashingEmbedder
from mcp_regulatory_rag.store import GuidanceChunk, GuidanceStore


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


SAMPLE_CHUNKS = [
    GuidanceChunk(
        document_id="tfda-aiml-samd-2020",
        title="人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引",
        jurisdiction="TW",
        doc_type="guidance",
        year=2020,
        page=12,
        chunk_index=0,
        heading="五、臨床效能驗證",
        text="申請者應提供獨立測試資料集之效能驗證結果，說明敏感度、特異度及其信賴區間，測試資料不得用於演算法訓練或調校。參考標準應由具資格之專科醫師建立。",
    ),
    GuidanceChunk(
        document_id="tfda-aiml-samd-2020",
        title="人工智慧/機器學習技術之醫療器材軟體查驗登記技術指引",
        jurisdiction="TW",
        doc_type="guidance",
        year=2020,
        page=14,
        chunk_index=1,
        heading="六、次族群分析",
        text="應分析不同年齡、性別、影像設備廠牌及醫療機構來源之次族群效能，以支持適應症範圍之宣稱。",
    ),
    GuidanceChunk(
        document_id="fda-cade-2022",
        title="FDA CADe Clinical Performance Assessment Guidance",
        jurisdiction="US",
        doc_type="guidance",
        year=2022,
        page=9,
        chunk_index=0,
        heading="Reader Study Design",
        text="A fully-crossed multiple-reader multiple-case (MRMC) design in which each reader interprets each case with and without the CADe device is recommended. An adequate washout period between reading sessions should be used to minimize memory bias.",
    ),
    GuidanceChunk(
        document_id="fda-cade-2022",
        title="FDA CADe Clinical Performance Assessment Guidance",
        jurisdiction="US",
        doc_type="guidance",
        year=2022,
        page=6,
        chunk_index=1,
        heading="Reference Standard",
        text="The reference standard (truth) should be established independently of the CADe output, by pathology or clinical follow-up where possible, or by a panel of qualified truthers with a pre-specified adjudication process.",
    ),
]


@pytest.fixture
def store():
    s = GuidanceStore(QdrantClient(":memory:"), HashingEmbedder(dim=64), collection="test_guidance")
    s.ensure_collection(recreate=True)
    s.upsert_chunks(SAMPLE_CHUNKS)
    return s
