"""secp256k1 conformance against the published cross-language vectors.

Its encoding has nothing in common with the post-quantum schemes, and every
test here exists because reusing the base64 path produces material the ledger
rejects as 1220 "Signature Incorrect" while saying nothing else.
"""

import base64

import pytest

pytest.importorskip("ecdsa", reason="needs the [ec] extra")

from activeledger import Secp256k1KeyPair  # noqa: E402
from activeledger.ec import is_high_s, is_high_s_base64  # noqa: E402
from activeledger.keys import KeyType  # noqa: E402


def test_both_public_key_forms_are_present(ec_vectors):
    # The ledger accepts either, so a port that only ever sees one never
    # learns to read the other.
    forms = {v["publicKeyForm"] for v in ec_vectors}

    assert "compressed" in forms
    assert "uncompressed" in forms
    assert len(ec_vectors) >= 12


def test_verifies_every_published_signature(ec_vectors):
    for v in ec_vectors:
        key = Secp256k1KeyPair.from_public_key(v["publicKey"])

        assert key.verify(
            v["message"].encode("utf-8"), base64.b64decode(v["signature"])
        ), f"failed to verify secp256k1/{v['messageName']}/{v['publicKeyForm']}"


def test_high_s_signatures_from_elsewhere_still_verify(ec_vectors):
    """High-S must still verify.

    The ledger verifies through OpenSSL, which neither normalises nor requires
    low-S, so it produces high-S freely. libsecp256k1 and Rust's k256 both
    reject high-S by default; python-ecdsa does not, which is why it is used
    here. A verifier enforcing low-S would reject roughly half of everything
    the ledger makes, and the half that succeeded would look like an
    intermittent fault.
    """
    high = [v for v in ec_vectors if is_high_s_base64(v["signature"])]

    assert high, "the published vectors no longer contain a high-S signature"

    for v in high:
        key = Secp256k1KeyPair.from_public_key(v["publicKey"])

        assert key.verify(
            v["message"].encode("utf-8"), base64.b64decode(v["signature"])
        ), (
            f"rejected a high-S signature ({v['messageName']}/{v['publicKeyForm']}) "
            "- low-S is being enforced on verify"
        )


def test_signatures_are_byte_identical_to_the_reference(ec_vectors):
    """The strongest test here: the exact bytes, not merely a valid signature.

    These expected values come from @noble/curves, an entirely separate
    implementation. Agreeing byte for byte means agreeing on RFC 6979's k, on
    low-S normalisation and on DER encoding at once -- none of which a
    verify-round-trip test can see. Only possible because ECDSA signing is
    deterministic; the post-quantum schemes are hedged and never can be.

    Without the low-S normalisation this SDK applies, 4 of these 12 differ.
    """
    for v in ec_vectors:
        key = Secp256k1KeyPair.from_keys(v["publicKey"], v["privateKey"])
        mine = base64.b64encode(key.sign(v["message"].encode("utf-8"))).decode()

        assert mine == v["deterministicSignature"], (
            f"{v['messageName']}/{v['publicKeyForm']}: signature differs from the "
            "reference. If r matches and only s differs, low-S normalisation is "
            "the cause."
        )


def test_signing_is_deterministic(ec_vectors):
    v = ec_vectors[0]
    key = Secp256k1KeyPair.from_keys(v["publicKey"], v["privateKey"])
    message = v["message"].encode("utf-8")

    assert key.sign(message) == key.sign(message)
    assert key.sign(message) != key.sign(ec_vectors[1]["message"].encode("utf-8"))


def test_every_signature_emitted_is_low_s():
    key = Secp256k1KeyPair.generate()

    for i in range(200):
        assert not is_high_s(key.sign(f"message {i}".encode())), f"signature {i} was high-S"


def test_signatures_made_here_verify_with_the_reference_key(ec_vectors):
    for v in ec_vectors:
        signer = Secp256k1KeyPair.from_keys(v["publicKey"], v["privateKey"])
        verifier = Secp256k1KeyPair.from_public_key(v["publicKey"])
        message = v["message"].encode("utf-8")

        assert verifier.verify(message, signer.sign(message))


def test_round_trips_published_keys_exactly(ec_vectors):
    for v in ec_vectors:
        key = Secp256k1KeyPair.from_keys(v["publicKey"], v["privateKey"])

        assert key.public_key == v["publicKey"]
        assert key.private_key == v["privateKey"]


def test_tampered_message_does_not_verify(ec_vectors):
    for v in ec_vectors:
        key = Secp256k1KeyPair.from_public_key(v["publicKey"])

        assert not key.verify(
            v["message"].encode("utf-8") + b" ", base64.b64decode(v["signature"])
        )


def test_generated_keys_use_the_ledgers_encoding():
    key = Secp256k1KeyPair.generate()

    assert key.public_key.startswith("0x")
    assert key.private_key.startswith("0x")
    # Compressed by default: 33 bytes, so "0x" plus 66 hex characters.
    assert len(key.public_key) == 68
    assert len(key.private_key) == 66
    assert key.public_key[2:4] in ("02", "03")


def test_uncompressed_generation_is_available():
    key = Secp256k1KeyPair.generate(compressed=False)

    assert len(key.public_key) == 132
    assert key.public_key.startswith("0x04")
    assert key.verify(b"x", key.sign(b"x"))


def test_private_keys_are_always_32_bytes():
    """A leading zero byte occurs roughly once in 400 keys, and a value that
    dropped it is a different scalar to anything reading it strictly."""
    for _ in range(1500):
        assert len(Secp256k1KeyPair.generate().private_key) == 66


def test_a_key_without_the_hex_prefix_is_refused_with_an_explanation():
    valid = Secp256k1KeyPair.generate().public_key

    with pytest.raises(ValueError, match="0x"):
        Secp256k1KeyPair.from_public_key(valid[2:])


def test_wrong_length_public_key_names_both_valid_lengths():
    with pytest.raises(ValueError) as error:
        Secp256k1KeyPair.from_public_key("0x" + "aa" * 20)

    assert "33" in str(error.value)
    assert "65" in str(error.value)


def test_a_prefix_that_contradicts_the_length_is_rejected():
    """A length and a point prefix that disagree means the forms got mixed."""
    with pytest.raises(ValueError, match="0x04"):
        Secp256k1KeyPair.from_public_key("0x04" + "aa" * 32)


def test_non_hex_is_rejected():
    with pytest.raises(ValueError, match="hex"):
        Secp256k1KeyPair.from_public_key("0xzzzz")


def test_verify_only_key_pair_refuses_to_sign(ec_vectors):
    key = Secp256k1KeyPair.from_public_key(ec_vectors[0]["publicKey"])

    assert not key.can_sign
    with pytest.raises(ValueError):
        key.sign(b"anything")
    with pytest.raises(ValueError):
        key.private_key


def test_malformed_signature_returns_false(ec_vectors):
    v = ec_vectors[0]
    key = Secp256k1KeyPair.from_public_key(v["publicKey"])
    message = v["message"].encode("utf-8")

    assert not key.verify(message, b"")
    assert not key.verify(message, bytes(10))
    # A raw r||s pair rather than DER.
    assert not key.verify(message, bytes(64))


def test_bitcoin_and_ethereum_parse_as_secp256k1():
    """The ledger routes these to identical verification, so an existing
    identity may carry either. They are never emitted."""
    for wire in ("bitcoin", "ethereum", "secp256k1"):
        assert KeyType.from_wire(wire) is KeyType.SECP256K1
        assert str(KeyType.from_wire(wire)) == "secp256k1"


def test_unknown_key_type_is_rejected():
    with pytest.raises(ValueError, match="Unknown key type"):
        KeyType.from_wire("ML-DSA-65")


def test_key_type_is_secp256k1():
    assert Secp256k1KeyPair.generate().key_type is KeyType.SECP256K1


def test_repr_does_not_leak_the_private_key():
    """repr ends up in logs."""
    key = Secp256k1KeyPair.generate()
    rendered = repr(key)

    assert key.private_key not in rendered
    assert key.public_key not in rendered
