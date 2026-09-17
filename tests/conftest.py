import base64
import json
from pathlib import Path

import pytest

VECTOR_FILE = Path(__file__).parent / "vectors" / "pq-vectors.json"


@pytest.fixture(scope="session")
def vectors():
    return json.loads(VECTOR_FILE.read_text())["vectors"]


@pytest.fixture(scope="session")
def reference_messages(vectors):
    """messageName -> the exact JSON.stringify output from the reference."""
    out = {}
    for v in vectors:
        out.setdefault(v["messageName"], v["message"])
    return out


def decode(value: str) -> bytes:
    return base64.b64decode(value)
