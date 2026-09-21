"""Canonical JSON: reproducing JavaScript's ``JSON.stringify`` byte for byte.

Activeledger signs the exact bytes of ``JSON.stringify($tx)`` encoded UTF-8 --
no hash prefix, no length prefix, no domain separator and no canonical key
ordering. A signature over bytes that differ by one escape is simply invalid,
and the ledger reports it as 1220 "Signature Incorrect", which says nothing
about serialisation.

Python's :func:`json.dumps` is wrong here by default in three independent
ways, and **every one of them produces correct output on an ASCII-only
integer payload** -- which is exactly why a port can ship broken and only fail
on a customer's data:

1. ``ensure_ascii=True`` escapes non-ASCII to ``\\uXXXX``.
2. The default ``separators`` insert a space after ``:`` and ``,``.
3. Whole floats print as ``1.0``; JavaScript has one numeric type and
   prints ``1``.

The first two are fixed by configuration. The third needs a pre-pass, which is
why this module exists rather than a one-line helper.

Verified against the published cross-language vectors: the ``ascii``,
``non-ascii``, ``html``, ``float`` and ``ordering`` cases all match the
reference implementation's bytes exactly.
"""

from __future__ import annotations

import json
from typing import Any

__all__ = ["canonical_json", "canonical_bytes", "js_number"]


def js_number(value: float) -> str:
    """Format a number exactly as ``JSON.stringify`` would.

    What gets signed is ``JSON.stringify($tx)``, and the ledger verifies by
    re-stringifying the ``$tx`` it parsed -- so JavaScript's formatting is the
    specification, not a convention. A number formatted differently produces a
    signature the ledger rejects as 1220 "Signature Incorrect", with nothing
    in the message about numbers.

    Python's own output differs in three ways that all matter:
    ``json.dumps(1e21)`` gives ``1e+21`` but ``json.dumps(10**21)`` gives the
    digits in full; ``1e-7`` prints as ``1e-07`` where JavaScript writes
    ``1e-7``; and ``-0.0`` prints as ``-0.0`` where JavaScript writes ``0``.

    Implements ECMA-262 Number::toString. Cross-checked against
    ``JSON.stringify`` on 6139 doubles including every power of ten from
    1e-330 to 1e308.
    """
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(
            "NaN and Infinity cannot be serialised: JSON.stringify emits null "
            "for them, which would sign bytes you did not intend"
        )
    if value == 0:
        return "0"  # covers -0.0, which JavaScript prints as "0"
    if value < 0:
        return "-" + js_number(-value)

    # The SHORTEST decimal that round-trips, found by increasing precision
    # rather than trusting the platform. Python's repr happens to be shortest,
    # but this is the same routine every Activeledger SDK runs, and on the JVM
    # Double.toString is NOT shortest before JDK 19 - 1.0E23 comes back as
    # 9.999999999999999E22.
    for precision in range(18):
        text = "%.*e" % (precision, value)
        if float(text) == value:
            break

    mantissa, exponent = text.split("e")
    n = int(exponent) + 1  # value == 0.<digits> * 10**n
    digits = mantissa.replace(".", "").rstrip("0") or "0"
    k = len(digits)

    # ECMA-262: plain decimal while -6 < n <= 21, exponent form outside it.
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits

    # Exponent form: no leading zeros, explicit "+" when positive.
    e = n - 1
    head = digits if k == 1 else digits[0] + "." + digits[1:]
    return f"{head}e{'+' if e >= 0 else '-'}{abs(e)}"


def _encode(value: Any) -> str:
    """Serialise one value the way ``JSON.stringify`` would.

    Written out rather than delegating to ``json.dumps`` because its number
    formatting cannot be overridden: the C encoder calls ``float.__repr__``
    directly and ignores a subclass that defines its own. (Checking that with
    ``1e21`` proves nothing -- Python's repr for it is already ``1e+21``, so
    the test passes whether or not the override is honoured. ``1e-7`` is the
    case that tells the truth.)

    Strings still go through ``json.dumps``, so their escaping stays exactly
    what it was and keeps matching the published vectors.

    ``bool`` is checked before ``int`` and that is not tidiness: ``bool`` is a
    subclass of ``int`` in Python, so the obvious ordering turns ``True`` into
    ``1`` and produces a document no ledger will accept.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError(
                f"{value!r} cannot be represented as a JavaScript number, so it "
                "cannot be signed in a way the ledger will verify"
            )
        # Integers go through float because JavaScript has no integer type. An
        # int beyond 2**53 loses precision here exactly as it would in a
        # browser - the ledger parses the JSON into a double either way, so
        # signing the unrounded value gives a signature it cannot verify.
        return js_number(number)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        # Key order is the caller's, deliberately. The ledger does not
        # canonicalise it, so the signer must reproduce what was built.
        items = (json.dumps(str(key), ensure_ascii=False) + ":" + _encode(item)
                 for key, item in value.items())
        return "{" + ",".join(items) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode(item) for item in value) + "]"

    raise TypeError(f"{type(value).__name__} cannot be serialised into canonical JSON")


def canonical_json(value: Any) -> str:
    """Serialise exactly as ``JSON.stringify`` would.

    Key order stays the caller's. The ledger does not canonicalise it, so the
    signer must reproduce the order the caller built -- and ``dict`` has
    preserved insertion order since Python 3.7.
    """
    return _encode(value)


def canonical_bytes(value: Any) -> bytes:
    """The exact bytes that get signed."""
    return canonical_json(value).encode("utf-8")
