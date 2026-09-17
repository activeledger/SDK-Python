"""Runs against a real 4-node Activeledger network.

Everything else in this repository checks the SDK against a published file.
This checks it against a running ledger, which is the only thing that actually
decides whether a signature is acceptable. A port can pass every unit test and
still be rejected by a node: the `type` string, the `$sigs` keying and the
exact signed bytes are all invisible to a unit test.

Start the network from an `activeledger` checkout::

    npm run test:network:serve

then run with the URLs it prints::

    AL_NODES=http://127.0.0.1:5510 AL_STORAGE=http://127.0.0.1:5509 pytest tests/integration

Skips when AL_NODES is unset, so the suite runs with no ledger present.
"""

import base64
import json
import os
import time
import urllib.parse
import urllib.request

import pytest

from activeledger import Activeledger, KeyType, TransactionBuilder

oqs = pytest.importorskip("oqs", reason="needs the [pq] extra")
from activeledger.pq import KeyPair  # noqa: E402

NODES = [n for n in os.environ.get("AL_NODES", "").split(",") if n.strip()]
STORAGE = [s for s in os.environ.get("AL_STORAGE", "").split(",") if s.strip()]

pytestmark = pytest.mark.skipif(
    not NODES, reason="AL_NODES not set - start 'npm run test:network:serve'"
)

EXPECTED_PUBLIC_BYTES = {KeyType.ML_DSA_65: 1952, KeyType.FALCON_512: 897}


def storage_read(index: int, doc_id: str) -> dict:
    """Read a document straight from a node's storage service.

    Deliberately here in the test and NOT in the SDK. Storage listens only on
    the node's own host, so it is not something a client can reach - the SDK
    reads state through a transaction's $r instead. This suite runs against a
    local harness where storage is reachable by definition, and uses it to
    assert what the ledger actually recorded rather than what a contract chose
    to hand back.
    """
    url = f"{STORAGE[index].rstrip('/')}/activeledger/{urllib.parse.quote(doc_id, safe='')}"
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode())


def unique(prefix: str) -> str:
    return f"{prefix}{int(time.time() * 1000) % 100000000}"


@pytest.mark.parametrize("key_type", [KeyType.ML_DSA_65, KeyType.FALCON_512])
def test_identity_onboards_and_is_recorded_correctly(key_type):
    ledger = Activeledger(NODES[0])
    identity = ledger.onboard(KeyPair.generate(key_type))
    assert identity.stream_id

    if not STORAGE:
        pytest.skip("AL_STORAGE not set - cannot verify what the ledger recorded")

    # Consensus is a majority, so the origin's reply means most nodes have
    # committed; the rest may still be writing.
    deadline = time.time() + 15
    meta = None
    while time.time() < deadline:
        try:
            meta = storage_read(0, f"{identity.stream_id}:stream")
            if meta.get("authorities"):
                break
        except Exception:
            pass
        time.sleep(0.5)

    assert meta and meta.get("authorities"), "identity meta never appeared"
    authority = meta["authorities"][0]
    assert authority["type"] == key_type.value
    assert len(base64.b64decode(authority["public"])) == EXPECTED_PUBLIC_BYTES[key_type]


@pytest.mark.parametrize("key_type", [KeyType.ML_DSA_65, KeyType.FALCON_512])
def test_a_transaction_signed_by_this_sdk_is_accepted(key_type):
    ledger = Activeledger(NODES[0])
    identity = ledger.onboard(KeyPair.generate(key_type))

    # Namespaces are claimed permanently, so a fixed name passes once and
    # fails every re-run against the same network - which reads exactly like
    # a regression and is not one.
    tx = (
        TransactionBuilder()
        .namespace("default")
        .contract("namespace")
        .input(identity.stream_id, identity.signer, {"namespace": unique("py")})
        .build()
    )
    response = ledger.submit(tx)
    assert response.committed, f"rejected: {response.raw}"


def test_a_tampered_payload_is_rejected():
    # Without this the suite would pass against an implementation that
    # accepted everything.
    ledger = Activeledger(NODES[0])
    identity = ledger.onboard(KeyPair.generate(KeyType.ML_DSA_65))

    honest = (
        TransactionBuilder()
        .namespace("default")
        .contract("namespace")
        .input(identity.stream_id, identity.signer, {"namespace": unique("pytamper")})
        .build()
    )
    # Same signature, different body - submitted raw, because the builder
    # would re-sign it into a valid transaction.
    tampered = honest.to_json().replace("pytamper", "pystolen")
    response = ledger.connection.submit_raw(tampered)
    assert not response.committed, f"a tampered payload was accepted: {response.raw}"
