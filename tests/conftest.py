import base64
import json
from pathlib import Path

import pytest

VECTOR_FILE = Path(__file__).parent / "vectors" / "pq-vectors.json"


@pytest.fixture(scope="session")
def vectors():
    """The post-quantum vectors only.

    The same file now carries secp256k1, whose key encoding and signature
    format differ in every respect; test_secp256k1 covers those. Returning
    them here would fail the length assertions that use this fixture.
    """
    all_vectors = json.loads(VECTOR_FILE.read_text())["vectors"]
    return [v for v in all_vectors if v["type"] in ("ml-dsa-65", "falcon-512")]


@pytest.fixture
def ec_vectors():
    """The secp256k1 vectors only."""
    all_vectors = json.loads(VECTOR_FILE.read_text())["vectors"]
    return [v for v in all_vectors if v["type"] == "secp256k1"]


@pytest.fixture(scope="session")
def reference_messages(vectors):
    """messageName -> the exact JSON.stringify output from the reference."""
    out = {}
    for v in vectors:
        out.setdefault(v["messageName"], v["message"])
    return out


def decode(value: str) -> bytes:
    return base64.b64decode(value)
