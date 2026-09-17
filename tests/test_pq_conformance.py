"""Conformance against the vectors published by the ledger repository.

This is what makes "done" an observation rather than an assertion: these
signatures were produced by the reference implementation and accepted by a
real network, so agreeing with them is agreeing with the thing that matters.
"""

import base64

import pytest

from activeledger.keys import KeyType

oqs = pytest.importorskip("oqs", reason="needs the [pq] extra")
from activeledger.pq import KeyPair  # noqa: E402

ALG = {"ml-dsa-65": KeyType.ML_DSA_65, "falcon-512": KeyType.FALCON_512}


def test_the_vector_file_has_both_schemes(vectors):
    # A file that silently lost a scheme would let everything below pass while
    # covering half of what it claims.
    types = {v["type"] for v in vectors}
    assert "ml-dsa-65" in types and "falcon-512" in types
    assert len(vectors) >= 12


def test_verifies_every_published_signature(vectors):
    for v in vectors:
        kp = KeyPair.from_public(ALG[v["type"]], v["publicKey"])
        assert kp.verify(v["message"].encode("utf-8"), base64.b64decode(v["signature"])), \
            f"failed to verify {v['type']}/{v['messageName']}"


def test_round_trips_published_keys_without_re_deriving(vectors):
    for v in vectors:
        kp = KeyPair.from_keys(ALG[v["type"]], v["publicKey"], v["privateKey"])
        assert kp.public_key_b64 == v["publicKey"]
        assert kp.private_key_b64 == v["privateKey"]


def test_signatures_made_here_verify_with_the_reference_public_key(vectors):
    for v in vectors:
        signer = KeyPair.from_keys(ALG[v["type"]], v["publicKey"], v["privateKey"])
        mine = signer.sign(v["message"].encode("utf-8"))
        verifier = KeyPair.from_public(ALG[v["type"]], v["publicKey"])
        assert verifier.verify(v["message"].encode("utf-8"), mine), \
            f"reference key rejected our {v['type']} signature"


def test_signing_is_hedged_so_two_signatures_differ(vectors):
    # Deliberately NOT byte equality against the vectors. The reference passes
    # fresh entropy on every sign, so no implementation can reproduce
    # another's bytes - and one that DID would be deterministic, a different
    # security posture adopted by accident.
    for v in vectors[:4]:
        kp = KeyPair.from_keys(ALG[v["type"]], v["publicKey"], v["privateKey"])
        message = v["message"].encode("utf-8")
        assert kp.sign(message) != kp.sign(message), \
            f"{v['type']} signing is deterministic; the reference is hedged"


def test_generated_key_sizes_match_the_ledger():
    sizes = {KeyType.ML_DSA_65: (1952, 4032), KeyType.FALCON_512: (897, 1281)}
    for key_type, (want_public, want_private) in sizes.items():
        kp = KeyPair.generate(key_type)
        assert len(base64.b64decode(kp.public_key_b64)) == want_public
        assert len(base64.b64decode(kp.private_key_b64)) == want_private


def test_falcon_signature_length_is_variable():
    # liboqs tables 752 for Falcon-512, which is the maximum buffer, not the
    # realised length. If this came back fixed, the algorithm ID would be
    # Falcon-padded-512 and every signature the wrong shape.
    kp = KeyPair.generate(KeyType.FALCON_512)
    lengths = {len(kp.sign(f"message {i}".encode())) for i in range(12)}
    assert len(lengths) > 1, f"falcon signature length looks fixed: {lengths}"
    assert all(600 < n < 700 for n in lengths), lengths


def test_mldsa_signature_length_is_fixed():
    kp = KeyPair.generate(KeyType.ML_DSA_65)
    assert {len(kp.sign(f"m{i}".encode())) for i in range(5)} == {3309}


def test_tampered_message_does_not_verify(vectors):
    for v in vectors:
        kp = KeyPair.from_public(ALG[v["type"]], v["publicKey"])
        tampered = (v["message"] + " ").encode("utf-8")
        assert not kp.verify(tampered, base64.b64decode(v["signature"]))


def test_malformed_signature_returns_false_rather_than_raising(vectors):
    v = vectors[0]
    kp = KeyPair.from_public(ALG[v["type"]], v["publicKey"])
    assert kp.verify(v["message"].encode(), b"") is False
    assert kp.verify(v["message"].encode(), b"\x00" * 10) is False


def test_signature_of_the_other_scheme_returns_false(vectors):
    mldsa = next(v for v in vectors if v["type"] == "ml-dsa-65")
    falcon = next(v for v in vectors if v["type"] == "falcon-512")
    kp = KeyPair.from_public(KeyType.ML_DSA_65, mldsa["publicKey"])
    assert kp.verify(mldsa["message"].encode(), base64.b64decode(falcon["signature"])) is False


def test_wrong_length_key_is_rejected_at_construction():
    short = base64.b64encode(b"\x00" * 100).decode()
    with pytest.raises(ValueError, match="1952"):
        KeyPair.from_public(KeyType.ML_DSA_65, short)


def test_falcon_keys_keep_their_header_byte():
    # Unlike BouncyCastle, liboqs emits Falcon keys WITH the 1-byte header,
    # so 897/1281. A codec shim added by analogy with the JVM SDK would
    # corrupt every key.
    kp = KeyPair.generate(KeyType.FALCON_512)
    assert base64.b64decode(kp.public_key_b64)[0] == 0x09
    assert base64.b64decode(kp.private_key_b64)[0] == 0x59


def test_verify_only_keypair_refuses_to_sign(vectors):
    v = vectors[0]
    kp = KeyPair.from_public(ALG[v["type"]], v["publicKey"])
    assert not kp.can_sign
    with pytest.raises(ValueError):
        kp.sign(b"x")


def test_repr_does_not_leak_key_material():
    kp = KeyPair.generate(KeyType.ML_DSA_65)
    assert kp.public_key_b64[:20] not in repr(kp)
