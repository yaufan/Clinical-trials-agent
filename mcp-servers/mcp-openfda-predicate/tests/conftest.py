import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).parent)
)  # for `_openfda_pdf_fixture` under --import-mode=importlib


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: hits real FDA endpoints; enabled with LIVE_API_TESTS=1"
    )
