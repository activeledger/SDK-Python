"""pq.KeyPair behaviour beyond the published vectors: generation, signing,
tamper detection, key validation and the verify-only / unsupported paths.

Needs liboqs, like test_pq_conformance. Without it these skip as a module.
"""

import base64
import subprocess
import sys
import textwrap

import pytest

from activeledger.keys import KeyType

pytest.importorskip("oqs", reason="needs the [pq] extra")
from activeledger.pq import KeyPair, PostQuantumUnavailable  # noqa: E402

SIZES = {KeyType.ML_DSA_65: (1952, 4032), KeyType.FALCON_512: (897, 1281)}
BOTH = pytest.mark.parametrize("key_type", list(SIZES), ids=lambda k: k.value)

MESSAGE = b'{"$namespace":"default","$contract":"c"}'


@pytest.fixture(scope="module", params=list(SIZES), ids=lambda k: k.value)
def pair(request):
    return KeyPair.generate(request.param)


# -- generation ---------------------------------------------------------------

def test_generated_keys_are_distinct_each_time(pair):
    other = KeyPair.generate(pair.key_type)
    assert other.public_key != pair.public_key
    assert other.private_key_b64 != pair.private_key_b64


def test_generated_pair_reports_its_type_and_can_sign(pair):
    assert pair.key_type in SIZES
    assert pair.can_sign is True


def test_encodings_are_base64_of_the_raw_ledger_lengths(pair):
    want_public, want_private = SIZES[pair.key_type]
    public = base64.b64decode(pair.public_key, validate=True)
    private = base64.b64decode(pair.private_key_b64, validate=True)
    assert (len(public), len(private)) == (want_public, want_private)
    # Canonical padding: re-encoding gives the same text back.
    assert base64.b64encode(public).decode() == pair.public_key
    assert base64.b64encode(private).decode() == pair.private_key_b64


def test_the_repr_carries_no_key_material(pair):
    text = repr(pair)
    assert pair.key_type.value in text and "public+private" in text
    assert pair.public_key[:24] not in text
    assert pair.private_key_b64[:24] not in text


# -- sign / verify --------------------------------------------------------------

def test_a_signature_verifies(pair):
    signature = pair.sign(MESSAGE)
    assert isinstance(signature, bytes)
    assert pair.verify(MESSAGE, signature) is True


def test_hedged_signatures_differ_and_both_verify(pair):
    first, second = pair.sign(MESSAGE), pair.sign(MESSAGE)
    assert first != second
    assert pair.verify(MESSAGE, first) and pair.verify(MESSAGE, second)


def test_a_tampered_message_is_rejected(pair):
    signature = pair.sign(MESSAGE)
    assert pair.verify(MESSAGE + b" ", signature) is False
    assert pair.verify(b"x" + MESSAGE[1:], signature) is False
    assert pair.verify(b"", signature) is False


def test_a_tampered_signature_is_rejected(pair):
    signature = bytearray(pair.sign(MESSAGE))
    for index in (0, len(signature) // 2, len(signature) - 1):
        tampered = bytearray(signature)
        tampered[index] ^= 0x01
        assert pair.verify(MESSAGE, bytes(tampered)) is False, f"flip at byte {index}"


def test_a_truncated_or_extended_signature_is_false_not_an_exception(pair):
    signature = pair.sign(MESSAGE)
    assert pair.verify(MESSAGE, signature[:-1]) is False
    assert pair.verify(MESSAGE, signature + b"\x00") is False
    assert pair.verify(MESSAGE, b"") is False


def test_another_identitys_signature_is_rejected(pair):
    stranger = KeyPair.generate(pair.key_type)
    assert pair.verify(MESSAGE, stranger.sign(MESSAGE)) is False


def test_an_empty_message_can_be_signed_and_verified(pair):
    assert pair.verify(b"", pair.sign(b"")) is True


def test_the_two_schemes_do_not_cross_verify():
    ml = KeyPair.generate(KeyType.ML_DSA_65)
    falcon = KeyPair.generate(KeyType.FALCON_512)
    assert falcon.verify(MESSAGE, ml.sign(MESSAGE)) is False
    assert ml.verify(MESSAGE, falcon.sign(MESSAGE)) is False


def test_ml_dsa_signatures_are_fixed_length_and_falcon_are_not():
    ml = KeyPair.generate(KeyType.ML_DSA_65)
    assert {len(ml.sign(f"m{i}".encode())) for i in range(4)} == {3309}


# -- restoring keys ----------------------------------------------------------------

def test_from_keys_restores_a_pair_that_interoperates(pair):
    restored = KeyPair.from_keys(pair.key_type, pair.public_key, pair.private_key_b64)
    assert restored.public_key == pair.public_key
    assert pair.verify(MESSAGE, restored.sign(MESSAGE))
    assert restored.verify(MESSAGE, pair.sign(MESSAGE))


def test_verify_only_key_verifies_but_cannot_sign(pair):
    public_only = KeyPair.from_public(pair.key_type, pair.public_key)
    assert public_only.can_sign is False
    assert public_only.verify(MESSAGE, pair.sign(MESSAGE)) is True
    assert public_only.verify(MESSAGE + b"!", pair.sign(MESSAGE)) is False
    assert "public only" in repr(public_only)


def test_verify_only_key_refuses_to_sign_or_export_a_private_key(pair):
    public_only = KeyPair.from_public(pair.key_type, pair.public_key)
    with pytest.raises(ValueError, match="verify-only"):
        public_only.sign(MESSAGE)
    with pytest.raises(ValueError, match="verify-only"):
        public_only.private_key_b64


# -- validation --------------------------------------------------------------------

@BOTH
def test_wrong_length_public_key_names_the_expected_length(key_type):
    want_public, _ = SIZES[key_type]
    for length in (0, want_public - 1, want_public + 1):
        with pytest.raises(ValueError, match=rf"public key should be {want_public} bytes, got {length}"):
            KeyPair(key_type, b"\x00" * length)


@BOTH
def test_wrong_length_private_key_names_the_expected_length(key_type):
    want_public, want_private = SIZES[key_type]
    for length in (0, want_private - 1, want_private + 1):
        with pytest.raises(ValueError, match=rf"private key should be {want_private} bytes, got {length}"):
            KeyPair(key_type, b"\x00" * want_public, b"\x00" * length)


def test_a_key_of_the_other_schemes_length_is_refused():
    falcon = KeyPair.generate(KeyType.FALCON_512)
    with pytest.raises(ValueError, match="should be 1952 bytes, got 897"):
        KeyPair.from_public(KeyType.ML_DSA_65, falcon.public_key)


@pytest.mark.parametrize("key_type", [KeyType.RSA, KeyType.SECP256K1])
def test_non_post_quantum_types_are_refused(key_type):
    with pytest.raises(ValueError, match="not a post-quantum type"):
        KeyPair(key_type, b"\x00" * 33)


def test_invalid_base64_is_reported_by_role(pair):
    with pytest.raises(ValueError, match="public key is not valid base64"):
        KeyPair.from_public(pair.key_type, "not base64!!")
    with pytest.raises(ValueError, match="private key is not valid base64"):
        KeyPair.from_keys(pair.key_type, pair.public_key, "not base64!!")


def test_a_non_string_key_is_a_type_error_not_a_base64_error(pair):
    with pytest.raises(TypeError, match="public key must be a string, got NoneType"):
        KeyPair.from_public(pair.key_type, None)
    with pytest.raises(TypeError, match="private key must be a string, got bytes"):
        KeyPair.from_keys(pair.key_type, pair.public_key, b"raw")


# -- no seed derivation --------------------------------------------------------------

@BOTH
def test_from_seed_is_not_implemented_and_says_why(key_type):
    with pytest.raises(NotImplementedError, match="liboqs") as info:
        KeyPair.from_seed(key_type, b"\x01" * 32)
    assert key_type.value in str(info.value)


@BOTH
def test_from_phrase_is_not_implemented_either(key_type):
    with pytest.raises(NotImplementedError, match="liboqs"):
        KeyPair.from_phrase(key_type, "abandon " * 11 + "about")


# -- liboqs absent ---------------------------------------------------------------------

def _without_liboqs(body: str) -> subprocess.CompletedProcess:
    blocker = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_spec(self, name, path=None, target=None):
                if name == "oqs" or name.startswith("oqs."):
                    raise ImportError("liboqs is not installed (blocked for this test)")
                return None

        sys.meta_path.insert(0, _Blocker())
        for _name in [m for m in sys.modules if m == "oqs" or m.startswith("oqs.")]:
            del sys.modules[_name]
        """
    )
    return subprocess.run(
        [sys.executable, "-c", blocker + textwrap.dedent(body)],
        capture_output=True, text=True, timeout=120,
    )


def test_a_key_built_from_bytes_needs_liboqs_only_to_sign_or_verify():
    result = _without_liboqs(
        f"""
        import base64
        from activeledger import KeyType, PostQuantumUnavailable
        from activeledger.pq import KeyPair

        public = base64.b64encode(b"\\x00" * 897).decode()
        private = base64.b64encode(b"\\x00" * 1281).decode()
        pair = KeyPair.from_keys(KeyType.FALCON_512, public, private)
        assert pair.public_key == public and pair.can_sign

        for call in (lambda: pair.sign(b"m"), lambda: pair.verify(b"m", b"s")):
            try:
                call()
            except PostQuantumUnavailable as exc:
                assert isinstance(exc, ImportError)
                assert "activeledger[pq]" in str(exc)
            else:
                raise AssertionError("expected PostQuantumUnavailable")
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_verify_does_not_turn_missing_liboqs_into_false():
    # verify() maps bad input to False; that must not also swallow "cannot
    # check at all", or an unverified signature would read as an invalid one.
    result = _without_liboqs(
        """
        import base64
        from activeledger import KeyType
        from activeledger.pq import KeyPair, PostQuantumUnavailable

        pair = KeyPair.from_public(KeyType.FALCON_512, base64.b64encode(b"\\x00" * 897).decode())
        try:
            outcome = pair.verify(b"m", b"s")
        except PostQuantumUnavailable:
            print("RAISED")
        else:
            print("RETURNED", outcome)
        """
    )
    assert result.returncode == 0, result.stderr
    assert "RAISED" in result.stdout


def test_postquantumunavailable_is_an_importerror():
    assert issubclass(PostQuantumUnavailable, ImportError)
