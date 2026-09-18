"""secp256k1, encoded the way Activeledger stores it.

Kept apart from :mod:`activeledger.pq` because almost nothing is shared.
Post-quantum keys are raw bytes in base64; these are hex with an ``0x``
prefix. Post-quantum signatures are fixed-length raw blobs; these are
variable-length DER. Folding the two together invites the one mistake that
matters here -- reusing a base64 path for a hex key, which produces material
the ledger rejects as 1220 "Signature Incorrect" while saying nothing else.

Needs the ``[ec]`` extra::

    pip install activeledger-sdk[ec]

``python-ecdsa`` is pure Python with no build step, unlike ``coincurve``
(libsecp256k1), which needs a C toolchain -- and which, unlike this, rejects
high-S signatures the ledger produces freely.
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from .keys import KeyType

try:
    from ecdsa import SECP256k1, SigningKey, VerifyingKey
    from ecdsa.util import sigdecode_der, sigencode_der

    _AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by test_no_ec_installed
    _AVAILABLE = False


#: SEC1 public key lengths. The ledger accepts both.
PUBLIC_KEY_COMPRESSED_SIZE = 33
PUBLIC_KEY_UNCOMPRESSED_SIZE = 65

#: The private scalar, always this many bytes.
PRIVATE_KEY_SIZE = 32

_MISSING = (
    "secp256k1 support needs the 'ec' extra: pip install activeledger-sdk[ec]. "
    "It installs python-ecdsa, which is pure Python and has no build step."
)


def _require() -> None:
    if not _AVAILABLE:
        raise ImportError(_MISSING)


def _order() -> int:
    return SECP256k1.order


def _half_order() -> int:
    return SECP256k1.order // 2


def _der_s(signature: bytes) -> int:
    """Pulls S out of a DER signature."""
    index = 2
    index += 2 + signature[index + 1]  # skip R
    length = signature[index + 1]
    return int.from_bytes(signature[index + 2 : index + 2 + length], "big")


def is_high_s(signature: bytes) -> bool:
    """Whether a DER signature's S is in the upper half of the curve order.

    Public because a test that cannot tell the two apart can prove neither
    that this SDK emits only low-S nor that it still accepts high-S from
    elsewhere.
    """
    _require()
    try:
        return _der_s(signature) > _half_order()
    except (IndexError, ValueError):
        return False


def is_high_s_base64(signature: str) -> bool:
    """:func:`is_high_s` for a base64 DER signature."""
    try:
        return is_high_s(base64.b64decode(signature))
    except Exception:
        return False


def _sigencode_der_low_s(r: int, s: int, order: int) -> bytes:
    """DER-encodes with S folded into the lower half of the order.

    ``python-ecdsa`` does NOT normalise, and it matters: without this, 4 of
    the 12 published vectors come out high-S and differ from the canonical
    form. Measured, not assumed.

    Low S is not for the ledger, which verifies through OpenSSL and accepts
    either. It is for ``@noble/curves`` -- the reference for the JavaScript
    side -- and for libsecp256k1 and Rust's ``k256``, all of which reject
    high-S by default. A signer emitting high-S roughly half the time fails
    against those roughly half the time, which reads as flakiness rather than
    as a signature format problem.
    """
    return sigencode_der(r, order - s if s > order // 2 else s, order)


class Secp256k1KeyPair:
    """A secp256k1 identity."""

    def __init__(
        self,
        verifying: "VerifyingKey",
        signing: Optional["SigningKey"],
        public_bytes: bytes,
    ) -> None:
        self._verifying = verifying
        self._signing = signing
        self._public_bytes = public_bytes

    # -- construction -----------------------------------------------------

    @classmethod
    def generate(cls, compressed: bool = True) -> "Secp256k1KeyPair":
        """Generates a key pair.

        Compressed by default: 33 bytes rather than 65, and this key is
        written into a transaction and then stored on an identity stream
        permanently. The ledger accepts either form.
        """
        _require()
        signing = SigningKey.generate(curve=SECP256k1)
        verifying = signing.get_verifying_key()

        return cls(
            verifying,
            signing,
            verifying.to_string("compressed" if compressed else "uncompressed"),
        )

    @classmethod
    def from_public_key(cls, public_key: str) -> "Secp256k1KeyPair":
        """A verify-only key pair from a stored public key."""
        _require()
        raw = _decode_hex(public_key, "public")
        _check_public(raw)

        return cls(VerifyingKey.from_string(raw, curve=SECP256k1), None, raw)

    @classmethod
    def from_keys(cls, public_key: str, private_key: str) -> "Secp256k1KeyPair":
        """Restores a signing key pair from stored key material."""
        pair = cls.from_public_key(public_key)

        scalar = _decode_hex(private_key, "private")
        if len(scalar) != PRIVATE_KEY_SIZE:
            raise ValueError(
                f"secp256k1 private key is {len(scalar)} bytes, expected {PRIVATE_KEY_SIZE}"
            )

        pair._signing = SigningKey.from_string(scalar, curve=SECP256k1)
        return pair

    # -- accessors --------------------------------------------------------

    @property
    def key_type(self) -> KeyType:
        return KeyType.SECP256K1

    @property
    def public_key(self) -> str:
        """The public key, ``0x``-prefixed hex, exactly as the ledger stores it."""
        return "0x" + self._public_bytes.hex()

    @property
    def private_key(self) -> str:
        """The private scalar, ``0x``-prefixed hex, always 32 bytes.

        Left-padded by ``to_string()``: a value that dropped a leading zero
        byte -- which happens to roughly one key in 400 -- is a different
        scalar to anything that reads it strictly.
        """
        if self._signing is None:
            raise ValueError(
                "This key pair has no private key - it was created for verification only"
            )
        return "0x" + self._signing.to_string().hex()

    @property
    def can_sign(self) -> bool:
        return self._signing is not None

    # -- signing ----------------------------------------------------------

    def sign(self, message: bytes) -> bytes:
        """Signs, deterministically (RFC 6979) and low-S.

        Deterministic k is about testability, not security: the same key and
        message give the same bytes in every correct implementation, so exact
        expected bytes can be published as cross-language vectors -- and an
        exact comparison is the only kind of test that can catch a low-S
        regression. A verify-round-trip test passes just as happily on a
        high-S signature.
        """
        if self._signing is None:
            raise ValueError(
                "This key pair has no private key - it was created for verification only"
            )

        return self._signing.sign_deterministic(
            message, hashfunc=hashlib.sha256, sigencode=_sigencode_der_low_s
        )

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verifies a signature, accepting HIGH-S as well as low.

        The ledger verifies through OpenSSL, which neither normalises nor
        requires low-S, so roughly half of everything it produces is high-S.
        A verifier that rejected those would fail on about half of all valid
        signatures, and the half that succeeded would make it look like an
        intermittent fault rather than a crypto one.

        ``python-ecdsa`` is permissive here by default -- measured against the
        published vectors, it accepts all 7 high-S cases -- unlike
        libsecp256k1 and ``k256``, which reject them. That is why this SDK
        uses it.

        Returns ``False`` rather than raising for malformed input: a caller
        checking a signature wants a yes or a no, and a signature of the wrong
        shape is a no.
        """
        try:
            return self._verifying.verify(
                signature, message, hashfunc=hashlib.sha256, sigdecode=sigdecode_der
            )
        except Exception:
            return False

    def __repr__(self) -> str:
        """Never prints private key material."""
        half = "public+private" if self.can_sign else "public only"
        return f"Secp256k1KeyPair({half})"


def _decode_hex(value: str, role: str) -> bytes:
    """Decodes an ``0x``-prefixed hex key.

    The prefix is required rather than tolerated: it is part of what the
    ledger stores, and a hex string without it can decode as base64 into
    plausible-looking bytes of the wrong length.
    """
    if not value.startswith("0x"):
        raise ValueError(
            f"secp256k1 {role} key must start with '0x' - that prefix is part of what "
            "the ledger stores, not decoration. Post-quantum keys are base64; these "
            "are not."
        )

    try:
        return bytes.fromhex(value[2:])
    except ValueError as error:
        raise ValueError(f"secp256k1 {role} key is not valid hex") from error


def _check_public(raw: bytes) -> None:
    """Checks the length and that the SEC1 point prefix agrees with it."""
    if len(raw) == PUBLIC_KEY_COMPRESSED_SIZE:
        compressed = True
    elif len(raw) == PUBLIC_KEY_UNCOMPRESSED_SIZE:
        compressed = False
    else:
        raise ValueError(
            f"secp256k1 public key is {len(raw)} bytes, expected "
            f"{PUBLIC_KEY_COMPRESSED_SIZE} (compressed) or "
            f"{PUBLIC_KEY_UNCOMPRESSED_SIZE} (uncompressed)"
        )

    prefix = raw[0]
    ok = prefix in (0x02, 0x03) if compressed else prefix == 0x04
    if not ok:
        raise ValueError(
            f"secp256k1 public key starts with 0x{prefix:02x}, which does not match "
            f"its length of {len(raw)} bytes (expected 0x02/0x03 for "
            f"{PUBLIC_KEY_COMPRESSED_SIZE}, 0x04 for {PUBLIC_KEY_UNCOMPRESSED_SIZE})"
        )
