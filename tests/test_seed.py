"""Seed and recovery-phrase derivation, against the published vectors.

Six other SDKs derive keys from the same seeds and phrases. A derivation that
drifts does not fail loudly - it produces a perfectly valid key for an
identity that is not the caller's, and the only symptom arrives much later as
1220 "Signature Incorrect" from somewhere else entirely.
"""

import json
from pathlib import Path

import pytest

from activeledger import recovery
from activeledger.keys import KeyType

VECTORS = json.loads((Path(__file__).parent / "vectors" / "seed-vectors.json").read_text())

SEED_VECTORS = VECTORS["seedVectors"]
PHRASE_VECTORS = VECTORS["phraseVectors"]

EC_SEEDS = [v for v in SEED_VECTORS if v["type"] == "secp256k1" and v.get("valid", True)]
EC_INVALID = [v for v in SEED_VECTORS if v["type"] == "secp256k1" and v.get("valid") is False]
EC_PHRASES = [v for v in PHRASE_VECTORS if v["type"] == "secp256k1"]


def _name(v):
    return f"{v.get('seedName') or v.get('phraseName')}/{v.get('publicKeyForm', '')}/{v.get('scheme', '')}"


# -- the derivation, independent of any key type -----------------------------


@pytest.mark.parametrize("v", [v for v in PHRASE_VECTORS if v["scheme"] == "v1"], ids=_name)
def test_derivation_matches_the_published_intermediates(v):
    """Checked separately from the key so a failure says WHICH step drifted."""
    bip39 = recovery.to_seed(v["phrase"], v["passphrase"])

    assert bip39.hex() == v["bip39Seed"]
    assert recovery.derive_seed(KeyType.from_wire(v["type"]), bip39).hex() == v["derivedSeed"]


def test_every_key_type_derives_a_different_seed_from_one_phrase():
    # Domain separation. Without it one phrase gives an ml-dsa-65 seed equal
    # to the secp256k1 scalar, so two identities share entropy.
    bip39 = recovery.to_seed(PHRASE_VECTORS[0]["phrase"])
    seeds = {
        recovery.derive_seed(t, bip39)
        for t in (KeyType.SECP256K1, KeyType.ML_DSA_65, KeyType.FALCON_512)
    }

    assert len(seeds) == 3


def test_seed_lengths_are_per_algorithm():
    bip39 = recovery.to_seed(PHRASE_VECTORS[0]["phrase"])

    assert len(recovery.derive_seed(KeyType.SECP256K1, bip39)) == 32
    assert len(recovery.derive_seed(KeyType.ML_DSA_65, bip39)) == 32
    assert len(recovery.derive_seed(KeyType.FALCON_512, bip39)) == 48


def test_a_passphrase_changes_the_seed():
    phrase = PHRASE_VECTORS[0]["phrase"]

    assert recovery.to_seed(phrase) != recovery.to_seed(phrase, "TREZOR")


def test_rsa_has_no_seed_derivation():
    bip39 = recovery.to_seed(PHRASE_VECTORS[0]["phrase"])

    with pytest.raises(ValueError, match="cannot be derived from a seed"):
        recovery.derive_seed(KeyType.RSA, bip39)


def test_a_bip39_seed_of_the_wrong_length_is_rejected():
    with pytest.raises(ValueError, match="64 bytes"):
        recovery.derive_seed(KeyType.SECP256K1, b"\x00" * 32)


# -- phrase validation -------------------------------------------------------


def test_a_phrase_with_a_bad_checksum_is_rejected():
    """An unchecked phrase is a silent failure: it derives a perfectly valid
    key for an identity nobody owns."""
    with pytest.raises(ValueError, match="checksum"):
        recovery.to_seed("abandon " * 11 + "abandon")


def test_a_word_outside_the_wordlist_is_named():
    with pytest.raises(ValueError, match="zzzz"):
        recovery.to_seed("abandon " * 11 + "zzzz")


def test_a_wrong_word_count_is_rejected():
    with pytest.raises(ValueError, match="12, 15, 18, 21 or 24"):
        recovery.to_seed("abandon abandon abandon")


def test_extra_whitespace_is_tolerated():
    phrase = PHRASE_VECTORS[0]["phrase"]

    assert recovery.to_seed(f"  {phrase}  ") == recovery.to_seed(phrase)


def test_the_wordlist_ships_with_the_package():
    # A wheel built without the package-data entry installs without it, and
    # the failure only appears at first use.
    from activeledger.recovery import _wordlist

    assert len(_wordlist()) == 2048


# -- secp256k1 ---------------------------------------------------------------

pytest.importorskip("ecdsa", reason="needs the [ec] extra")

from activeledger import Secp256k1KeyPair  # noqa: E402


@pytest.mark.parametrize("v", EC_SEEDS, ids=_name)
def test_from_seed_reproduces_the_published_key(v):
    key = Secp256k1KeyPair.from_seed(
        bytes.fromhex(v["seed"]), v["publicKeyForm"] == "compressed"
    )

    assert key.public_key == v["publicKey"]
    assert key.private_key == v["privateKey"]


@pytest.mark.parametrize("v", EC_INVALID, ids=_name)
def test_an_invalid_scalar_is_refused_rather_than_reduced(v):
    """Reducing mod n returns a working key for a different identity, and
    nothing downstream ever reports a problem."""
    with pytest.raises(ValueError, match=r"\[1, n-1\]"):
        Secp256k1KeyPair.from_seed(bytes.fromhex(v["seed"]))


@pytest.mark.parametrize("v", EC_PHRASES, ids=_name)
def test_phrase_recovery_reproduces_the_published_key(v):
    compressed = v["publicKeyForm"] == "compressed"
    key = (
        Secp256k1KeyPair.from_legacy_phrase(v["phrase"], compressed)
        if v["scheme"] == "legacy"
        else Secp256k1KeyPair.from_phrase(v["phrase"], v["passphrase"], compressed)
    )

    assert key.public_key == v["publicKey"]
    assert key.private_key == v["privateKey"]


@pytest.mark.parametrize("length", [31, 33, 48, 0])
def test_a_seed_of_the_wrong_length_is_refused_rather_than_padded(length):
    # Padding would produce a valid key for a different identity - the same
    # failure as reducing a scalar, by another route.
    with pytest.raises(ValueError, match="32-byte seed"):
        Secp256k1KeyPair.from_seed(b"\x01" * length)


def test_a_seed_derived_key_signs_and_verifies():
    key = Secp256k1KeyPair.from_seed(b"\x11" * 32)

    assert key.verify(b"payload", key.sign(b"payload"))


def test_the_same_seed_always_derives_the_same_key():
    assert (
        Secp256k1KeyPair.from_seed(b"\x5a" * 32).public_key
        == Secp256k1KeyPair.from_seed(b"\x5a" * 32).public_key
    )


# -- the post-quantum gap ----------------------------------------------------


def test_post_quantum_from_seed_explains_why_it_cannot():
    """Raised rather than left as an AttributeError, so someone porting code
    from another SDK finds out here rather than from a rejected signature."""
    pytest.importorskip("oqs", reason="needs the [pq] extra")
    from activeledger.pq import KeyPair

    with pytest.raises(NotImplementedError, match="derandomised signature keygen"):
        KeyPair.from_seed(KeyType.ML_DSA_65, b"\x00" * 32)
