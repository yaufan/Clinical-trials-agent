import json
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def study_fixture() -> dict:
    return json.loads((FIXTURES / "nct06018545.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def search_fixture() -> dict:
    return json.loads((FIXTURES / "search_ich_ai.json").read_text(encoding="utf-8"))
