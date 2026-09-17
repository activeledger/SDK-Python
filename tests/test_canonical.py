import pytest

from activeledger.canonical import canonical_bytes, canonical_json

# Python's json.dumps is wrong here by default in three independent ways, and
# every one produces correct output on an ASCII-only integer payload - which
# is exactly why a port can ship broken and only fail on a customer's data.


def test_ascii_baseline(reference_messages):
    assert canonical_json({"greeting": "hello"}) == reference_messages["ascii"]


def test_non_ascii_matches_reference(reference_messages):
    # ensure_ascii=True would escape these to \uXXXX and sign different bytes.
    assert canonical_json({"greeting": "café 日本語 ☕"}) == \
        reference_messages["non-ascii"]


def test_html_characters_are_not_escaped(reference_messages):
    assert canonical_json({"expr": "a < b && c > d", "amp": "Tom & Jerry"}) == \
        reference_messages["html"]


def test_whole_floats_print_as_integers(reference_messages):
    # json.dumps(1.0) gives "1.0"; JavaScript has one numeric type and gives "1".
    assert canonical_json({"whole": 1.0, "third": 0.1, "negative": -2.5, "zero": 0}) == \
        reference_messages["float"]


def test_key_order_is_insertion_order_not_sorted(reference_messages):
    # The ledger does not canonicalise key order, so the signer reproduces
    # whatever order the caller built. These keys are not alphabetical.
    assert canonical_json({"zebra": 1, "alpha": 2, "middle": 3}) == \
        reference_messages["ordering"]


def test_booleans_are_not_turned_into_numbers():
    # bool is a subclass of int in Python, so a whole-float-to-int conversion
    # written the obvious way turns True into 1.
    assert canonical_json({"t": True, "f": False}) == '{"t":true,"f":false}'


def test_booleans_inside_nested_structures_survive():
    assert canonical_json({"a": [True, False, 1.0]}) == '{"a":[true,false,1]}'


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_infinity_are_refused(bad):
    # json.dumps emits NaN / Infinity, which are not JSON and would sign bytes
    # no other implementation can read.
    with pytest.raises(ValueError):
        canonical_json({"x": bad})


def test_nested_structures_and_arrays():
    assert canonical_json({"a": [1, "two", True, None], "b": {"c": False}}) == \
        '{"a":[1,"two",true,null],"b":{"c":false}}'


def test_floats_inside_nested_structures_are_converted():
    assert canonical_json({"outer": {"inner": [1.0, 2.5]}}) == '{"outer":{"inner":[1,2.5]}}'


def test_empty_containers():
    assert canonical_json({}) == "{}"
    assert canonical_json([]) == "[]"


def test_escapes_only_what_json_requires():
    assert canonical_json({"s": 'a"b\\c'}) == '{"s":"a\\"b\\\\c"}'


def test_canonical_bytes_is_utf8_of_the_string():
    obj = {"e": "é"}
    assert canonical_bytes(obj) == canonical_json(obj).encode("utf-8")
    assert len(canonical_bytes(obj)) == 10  # accented e is two bytes


def test_onboard_shape_matches_reference(reference_messages):
    import re
    reference = reference_messages["onboard"]
    public_key = re.search(r'"publicKey":"([^"]+)"', reference).group(1)
    key_type = re.search(r'"type":"([^"]+)"', reference).group(1)
    built = {
        "$namespace": "default",
        "$contract": "onboard",
        "$i": {"identity": {"type": key_type, "publicKey": public_key}},
        "$o": {},
    }
    assert canonical_json(built) == reference
