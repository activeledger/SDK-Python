import base64
import json

import pytest

from activeledger.canonical import canonical_bytes, canonical_json
from activeledger.keys import KeyType
from activeledger.transaction import TransactionBuilder, onboard_transaction


class StubSigner:
    """A Signer that needs no crypto, so these tests run without the extra."""

    def __init__(self, key_type=KeyType.ML_DSA_65, public="PUBLICKEY"):
        self._key_type = key_type
        self._public = public
        self.signed = []

    @property
    def key_type(self):
        return self._key_type

    @property
    def public_key_b64(self):
        return self._public

    def sign(self, message: bytes) -> bytes:
        self.signed.append(message)
        return b"SIGNATURE-" + message[:8]


def test_onboard_is_selfsign_and_keyed_by_label():
    # $sigs is keyed by the $i LABEL, not a stream id - there is no stream
    # yet. This is the most likely first integration failure in any port.
    tx = onboard_transaction(StubSigner())
    assert tx.self_sign is True
    assert set(tx.sigs) == {"identity"}
    assert set(tx.body["$i"]) == {"identity"}


def test_onboard_always_carries_an_explicit_type():
    # The ledger defaults a missing type to "rsa" and then verifies RSA
    # against a base64 post-quantum blob, reported as 1220.
    tx = onboard_transaction(StubSigner(KeyType.FALCON_512))
    assert tx.body["$i"]["identity"]["type"] == "falcon-512"


def test_onboard_signature_covers_the_body_not_the_envelope():
    signer = StubSigner()
    tx = onboard_transaction(signer)
    assert signer.signed == [canonical_bytes(tx.body)]
    assert signer.signed[0] != canonical_bytes(tx.envelope())


def test_custom_label_used_for_input_and_signature():
    tx = onboard_transaction(StubSigner(), label="mylabel")
    assert set(tx.sigs) == {"mylabel"} and set(tx.body["$i"]) == {"mylabel"}


def test_signed_bytes_are_the_canonical_body():
    tx = onboard_transaction(StubSigner())
    assert tx.signed_bytes() == canonical_json(tx.body).encode("utf-8")


def test_builder_requires_namespace_contract_and_signer():
    signer = StubSigner()
    with pytest.raises(ValueError, match="namespace"):
        TransactionBuilder().contract("c").input("s", signer).build()
    with pytest.raises(ValueError, match="contract"):
        TransactionBuilder().namespace("n").input("s", signer).build()
    with pytest.raises(ValueError, match="input"):
        TransactionBuilder().namespace("n").contract("c").build()


def test_builder_preserves_insertion_order():
    tx = (
        TransactionBuilder()
        .namespace("default")
        .contract("demo")
        .input("streamA", StubSigner(), {"zebra": 1, "alpha": 2})
        .build()
    )
    body = canonical_json(tx.body)
    assert body.index("zebra") < body.index("alpha")


def test_readonly_adds_dollar_r_only_when_used():
    signer = StubSigner()
    without = TransactionBuilder().namespace("n").contract("c").input("s", signer).build()
    assert "$r" not in without.body

    with_r = (
        TransactionBuilder().namespace("n").contract("c")
        .input("s", signer).readonly("target", "streamXYZ").build()
    )
    assert with_r.body["$r"] == {"target": "streamXYZ"}


def test_entry_emitted_only_when_set():
    signer = StubSigner()
    assert "$entry" not in TransactionBuilder().namespace("n").contract("c").input("s", signer).build().body
    tx = TransactionBuilder().namespace("n").contract("c").entry("update").input("s", signer).build()
    assert tx.body["$entry"] == "update"


def test_outputs_included_only_when_present():
    signer = StubSigner()
    tx = (
        TransactionBuilder().namespace("n").contract("c")
        .input("s", signer).output("target", {"message": "hi"}).build()
    )
    assert tx.body["$o"] == {"target": {"message": "hi"}}


def test_multiple_inputs_each_get_a_signature():
    a, b = StubSigner(), StubSigner(KeyType.FALCON_512)
    tx = (
        TransactionBuilder().namespace("n").contract("c")
        .input("streamA", a).input("streamB", b).build()
    )
    assert list(tx.sigs) == ["streamA", "streamB"]
    # Both signed the identical body.
    assert a.signed[0] == b.signed[0] == tx.signed_bytes()


def test_non_ascii_payload_signs_the_canonical_bytes():
    signer = StubSigner()
    tx = (
        TransactionBuilder().namespace("default").contract("demo")
        .input("streamA", signer, {"note": "café 日本語"}).build()
    )
    serialised = tx.signed_bytes().decode("utf-8")
    assert "café" in serialised
    assert "\\u00e9" not in serialised


def test_envelope_is_submittable_json():
    tx = onboard_transaction(StubSigner())
    envelope = json.loads(tx.to_json())
    assert envelope["$selfsign"] is True
    assert "$tx" in envelope and "$sigs" in envelope

    ordinary = TransactionBuilder().namespace("n").contract("c").input("s", StubSigner()).build()
    assert "$selfsign" not in json.loads(ordinary.to_json())


def test_signatures_are_base64():
    tx = onboard_transaction(StubSigner())
    base64.b64decode(tx.sigs["identity"], validate=True)
