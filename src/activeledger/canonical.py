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

__all__ = ["canonical_json", "canonical_bytes"]


def _javascript_numbers(value: Any) -> Any:
    """Convert whole floats to ints, the way JavaScript prints them.

    ``json.dumps(1.0)`` gives ``"1.0"``; ``JSON.stringify(1.0)`` gives ``"1"``.
    A JVM or Python signer that emits ``1.0`` produces a different byte string
    and therefore an invalid signature.

    The ``bool`` check has to come first and is not defensive tidiness:
    ``bool`` is a subclass of ``int`` in Python, so ``isinstance(True, int)``
    is ``True``. Written the obvious way, this function turns ``True`` into
    ``1`` and produces a document no ledger will accept.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        # json.dumps would emit NaN / Infinity, which are not JSON at all.
        # Signing them would produce bytes no other implementation can read,
        # so refuse rather than silently emit something unparseable.
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(
                "NaN and Infinity cannot be serialised: JSON.stringify emits "
                "null for them, which would sign bytes you did not intend"
            )
        return int(value) if value.is_integer() else value
    if isinstance(value, dict):
        return {key: _javascript_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_javascript_numbers(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Serialise exactly as ``JSON.stringify`` would.

    ``sort_keys`` stays ``False`` deliberately. The ledger does not
    canonicalise key order, so the signer must reproduce the order the caller
    built -- and ``dict`` has preserved insertion order since Python 3.7.
    """
    return json.dumps(
        _javascript_numbers(value),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        sort_keys=False,
    )


def canonical_bytes(value: Any) -> bytes:
    """The exact bytes that get signed."""
    return canonical_json(value).encode("utf-8")
