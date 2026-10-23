import json
import os
import pathlib

import httpx
import pytest
import respx

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def efetch_xml() -> str:
    return (FIXTURES / "efetch_two_articles.xml").read_text(encoding="utf-8")


@pytest.fixture
def esearch_json() -> dict:
    return {
        "header": {"type": "esearch", "version": "0.3"},
        "esearchresult": {
            "count": "2",
            "retmax": "20",
            "retstart": "0",
            "idlist": ["31000001", "31000002"],
            "querytranslation": '"intracranial hemorrhages"[MeSH Terms] AND sensitivity[tiab]',
            "translationset": [],
        },
    }


@pytest.fixture
def esummary_json() -> dict:
    return {
        "header": {"type": "esummary", "version": "0.3"},
        "result": {
            "uids": ["31000001"],
            "31000001": {
                "uid": "31000001",
                "pubdate": "2021 Feb",
                "source": "Radiology",
                "fulljournalname": "Radiology",
                "authors": [
                    {"name": "Smith JA", "authtype": "Author"},
                    {"name": "Lee K", "authtype": "Author"},
                ],
                "title": "Diagnostic Performance of Radiologists for Acute Intracranial Hemorrhage.",
                "volume": "298",
                "issue": "2",
                "pages": "345-53",
                "elocationid": "doi: 10.1148/radiol.2021000001",
                "articleids": [
                    {"idtype": "pubmed", "idtypen": 1, "value": "31000001"},
                    {"idtype": "doi", "idtypen": 3, "value": "10.1148/radiol.2021000001"},
                    {"idtype": "pmc", "idtypen": 8, "value": "PMC7000001"},
                ],
                "pubtype": ["Journal Article", "Multicenter Study"],
            },
        },
    }


@pytest.fixture
def mocked_eutils(esearch_json, esummary_json, efetch_xml):
    """respx router with the three endpoints wired to the fixtures."""
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        router.get("esearch.fcgi").mock(return_value=httpx.Response(200, json=esearch_json))
        router.get("esummary.fcgi").mock(return_value=httpx.Response(200, json=esummary_json))
        router.get("efetch.fcgi").mock(return_value=httpx.Response(200, text=efetch_xml))
        yield router


def pytest_collection_modifyitems(config, items):
    if os.environ.get("LIVE_API_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="live NCBI tests disabled (set LIVE_API_TESTS=1)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())
