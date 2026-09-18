"""secp256k1 against a real 4-node Activeledger network.

Separate from test_live_network.py, which imports activeledger.pq at module
level and therefore skips entirely without liboqs. secp256k1 needs only the
[ec] extra, and a test that silently skips for an unrelated missing
dependency reports coverage nobody has.

Start the network from an activeledger checkout::

    npm run test:network:serve

then run with the URLs it prints::

    AL_NODES=http://127.0.0.1:5510 AL_STORAGE=http://127.0.0.1:5509 \
        pytest tests/integration -q
"""

import json
import os
import time
import urllib.parse
import urllib.request

import pytest

pytest.importorskip("ecdsa", reason="needs the [ec] extra")

from activeledger import Activeledger  # noqa: E402
from activeledger.ec import Secp256k1KeyPair  # noqa: E402

NODES = [u for u in os.environ.get("AL_NODES", "").split(",") if u]
STORAGE = [u for u in os.environ.get("AL_STORAGE", "").split(",") if u]

pytestmark = pytest.mark.skipif(
    not NODES, reason="AL_NODES not set - start 'npm run test:network:serve'"
)


def storage_read(index: int, stream_id: str) -> dict:
    """Reads a document straight from a node's storage service.

    Deliberately here and NOT in the SDK: storage listens only on the node's
    own host, so a real client cannot reach it and reads state through a
    transaction's $r instead. This harness runs locally, where storage is
    reachable by definition, and it is used to assert what the ledger
    RECORDED rather than what a contract chose to report.
    """
    base = STORAGE[index].rstrip("/")
    url = f"{base}/activeledger/{urllib.parse.quote(stream_id, safe='')}"
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode())


def unique(prefix: str) -> str:
    return f"{prefix}{int(time.time() * 1000) % 100000000}"


def await_authorities(stream_id: str):
    """Consensus is a majority, so the origin's reply means most nodes have
    committed; the rest may still be writing."""
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            meta = storage_read(0, f"{stream_id}:stream")
            if meta.get("authorities"):
                return meta["authorities"]
        except Exception:
            pass
        time.sleep(0.5)

    pytest.fail(f"stream meta for {stream_id} never appeared")


@pytest.mark.parametrize(
    "compressed,expected_chars", [(True, 68), (False, 132)]
)
def test_secp256k1_identity_onboards_and_is_recorded_correctly(compressed, expected_chars):
    """The ledger accepts both public key forms and tells them apart by
    length, so onboarding only ever with the compressed form would leave the
    other path unproven."""
    ledger = Activeledger(NODES[0])
    key = Secp256k1KeyPair.generate(compressed=compressed)
    identity = ledger.onboard(key)
    assert identity.stream_id

    if not STORAGE:
        pytest.skip("AL_STORAGE not set - cannot verify what the ledger recorded")

    authority = await_authorities(identity.stream_id)[0]

    assert authority["type"] == "secp256k1"

    # Stored as 0x-prefixed hex, NOT base64. If this ever comes back base64
    # the SDK has encoded it the post-quantum way, and every later signature
    # fails as 1220.
    stored = authority["public"]
    assert stored.startswith("0x"), f"the ledger stored {stored!r}, which is not 0x hex"
    assert len(stored) == expected_chars
    assert stored == key.public_key


def test_a_secp256k1_signed_transaction_is_accepted():
    ledger = Activeledger(NODES[0])
    key = Secp256k1KeyPair.generate()
    identity = ledger.onboard(key)

    tx = (
        Activeledger.transaction()
        .namespace("default")
        .contract("namespace")
        .input(identity.stream_id, key, {"namespace": unique("pyec")})
        .build()
    )

    response = ledger.submit(tx)
    assert response.committed, response.raw
