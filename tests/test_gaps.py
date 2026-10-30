"""Edge cases in canonical JSON, secp256k1 helpers, key types and the wordlist."""

import pytest

from activeledger import recovery
from activeledger.canonical import canonical_bytes, canonical_json
from activeledger.keys import KeyType


# -- canonical JSON ---------------------------------------------------------------

@pytest.mark.parametrize("bad", [object(), {1, 2}, b"bytes", 1 + 2j])
def test_unserialisable_types_raise_rather_than_signing_a_guess(bad):
    with pytest.raises(TypeError, match="cannot be serialised"):
        canonical_json({"x": bad})


def test_the_type_error_names_the_offending_type():
    with pytest.raises(TypeError, match="set"):
        canonical_json({"x": {1}})


def test_tuples_serialise_as_arrays():
    assert canonical_json({"t": (1, "a", None)}) == '{"t":[1,"a",null]}'


def test_non_string_keys_are_stringified_like_javascript():
    assert canonical_json({1: "a", 2: "b"}) == '{"1":"a","2":"b"}'


def test_control_characters_are_escaped():
    assert canonical_json({"s": "a\nb\tc\u0001"}) == '{"s":"a\\nb\\tc\\u0001"}'


def test_integers_are_printed_as_javascript_doubles():
    # JSON.stringify(1e21) is "1e+21": JavaScript has no integer type.
    assert canonical_json({"n": 10**21}) == '{"n":1e+21}'
    assert canonical_json({"n": 10**20}) == '{"n":100000000000000000000}'


def test_a_top_level_scalar_is_serialised_bare():
    assert canonical_json("é") == '"é"'
    assert canonical_json(None) == "null"
    assert canonical_bytes(7) == b"7"


def test_a_bad_value_deep_in_the_document_is_still_refused():
    with pytest.raises(ValueError):
        canonical_json({"a": [{"b": [float("nan")]}]})


# -- key types ---------------------------------------------------------------------

@pytest.mark.parametrize("wire", ["rsa", "secp256k1", "ml-dsa-65", "falcon-512"])
def test_every_emitted_wire_value_round_trips(wire):
    assert KeyType.from_wire(wire).value == wire


@pytest.mark.parametrize("wire", ["", "RSA", "Secp256k1", " rsa", "ml-dsa-44", "bitcoin "])
def test_near_misses_are_rejected(wire):
    with pytest.raises(ValueError, match="Unknown key type"):
        KeyType.from_wire(wire)


def test_only_the_lattice_schemes_are_post_quantum():
    assert KeyType.ML_DSA_65.is_post_quantum and KeyType.FALCON_512.is_post_quantum
    assert not KeyType.RSA.is_post_quantum and not KeyType.SECP256K1.is_post_quantum


# -- wordlist integrity -----------------------------------------------------------------

@pytest.fixture
def broken_wordlist(monkeypatch, tmp_path):
    """Points recovery at a replacement wordlist and drops the cached one."""
    recovery._wordlist.cache_clear()

    def install(text=None):
        path = tmp_path / "words.txt"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        monkeypatch.setattr(recovery, "_WORDLIST_FILE", path)

    yield install
    recovery._wordlist.cache_clear()


def test_a_missing_wordlist_is_reported_by_path(broken_wordlist):
    broken_wordlist(None)

    with pytest.raises(RuntimeError, match="wordlist is missing"):
        recovery._wordlist()


def test_a_truncated_wordlist_is_refused_with_the_count(broken_wordlist):
    broken_wordlist("abandon\nability\nable\n")

    with pytest.raises(RuntimeError, match="2048 words, found 3"):
        recovery._wordlist()
