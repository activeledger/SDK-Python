"""Canonical number formatting, against the published vectors.

What gets signed is ``JSON.stringify($tx)`` and the ledger verifies by
re-stringifying the ``$tx`` it parsed, so JavaScript's number formatting is
the specification. A number formatted differently produces a signature the
ledger rejects as 1220, with nothing in the message about numbers.

These exist because the `float` case in pq-vectors.json -- 1, 0.1, -2.5, 0 --
sits entirely inside the range where every language already agrees.
"""

import json
from pathlib import Path

import pytest

from activeledger import canonical_json
from activeledger.canonical import js_number

VECTORS = json.loads((Path(__file__).parent / "vectors" / "number-vectors.json").read_text())["vectors"]


@pytest.mark.parametrize("v", VECTORS, ids=lambda v: v["name"])
def test_js_number_matches_the_reference(v):
    assert js_number(float(v["value"])) == v["expected"]


@pytest.mark.parametrize("v", VECTORS, ids=lambda v: v["name"])
def test_canonical_json_uses_it(v):
    # The formatter being right is not enough if the encoder does not call it.
    # json.dumps ignores a float subclass's __repr__, so an earlier attempt at
    # this produced correct js_number output and wrong canonical output.
    assert canonical_json({"n": float(v["value"])}) == '{"n":' + v["expected"] + "}"


def test_negative_zero_loses_its_sign():
    assert canonical_json({"n": -0.0}) == '{"n":0}'


def test_integers_beyond_2_53_take_double_precision():
    # JavaScript has no integer type, so the ledger parses this into a double
    # whatever we send. Signing the unrounded value gives a signature it
    # cannot verify.
    assert canonical_json({"n": 9007199254740993}) == '{"n":9007199254740992}'


def test_exponent_has_no_leading_zeros():
    assert canonical_json({"n": 1e-7}) == '{"n":1e-7}'
    assert canonical_json({"n": 1e21}) == '{"n":1e+21}'


def test_the_plain_exponent_boundaries():
    # Both sides of both boundaries: this is where implementations part company.
    assert canonical_json({"n": 1e20}) == '{"n":100000000000000000000}'
    assert canonical_json({"n": 1e21}) == '{"n":1e+21}'
    assert canonical_json({"n": 1e-6}) == '{"n":0.000001}'
    assert canonical_json({"n": 1e-7}) == '{"n":1e-7}'


def test_non_finite_is_refused():
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="cannot be represented|cannot be serialised"):
            canonical_json({"n": bad})


def test_booleans_are_not_numbers():
    # bool subclasses int in Python; the obvious ordering emits 1 and 0.
    assert canonical_json({"t": True, "f": False}) == '{"t":true,"f":false}'
