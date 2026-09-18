"""Post-quantum key pairs, backed by liboqs.

Requires the optional extra::

    pip install 'activeledger-sdk[pq]'

**No key codec here, deliberately.** liboqs already produces and accepts the
exact byte forms the ledger uses -- including Falcon's 1-byte header, so keys
are 897/1281 rather than the 896/1280 BouncyCastle returns. A shim added by
analogy with the JVM SDK would corrupt every key. Verified 2026-09-18 against
the published cross-language vectors.

Signing is whatever liboqs does natively, which is hedged. The JavaScript
reference is hedged too -- it passes fresh entropy on every sign so it does not
depend on a global RNG -- so **no implementation can reproduce another's
signature bytes and none should try**. Verify, never reproduce.
"""

from __future__ import annotations

import base64
from typing import Optional

from .keys import PQ_EXTRA_HINT, KeyType

__all__ = ["KeyPair", "PostQuantumUnavailable"]


class PostQuantumUnavailable(ImportError):
    """Raised when the ``[pq]`` extra is not installed."""


def _oqs():
    """Import liboqs lazily, with an error that says what to do.

    Lazy so that importing this SDK, building a transaction and submitting it
    all work with no compiled dependency present. The message names the extra
    rather than letting a CMake traceback from inside a dependency be the
    user's first contact with the problem.
    """
    try:
        import oqs  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised in a clean venv
        raise PostQuantumUnavailable(
            f"{KeyType.ML_DSA_65.value} / {KeyType.FALCON_512.value} need "
            f"liboqs.\n\n{PQ_EXTRA_HINT}"
        ) from exc
    return oqs


# The ledger's wire strings mapped to liboqs mechanism names.
#
# Falcon-512, NOT Falcon-padded-512. liboqs exposes both, and they are
# different formats: the padded variant emits fixed-length signatures, while
# the ledger's peers produce the compressed variable-length form (653-657
# bytes observed). Picking the wrong one here produces signatures that are
# individually well-formed and universally rejected.
_MECHANISM = {
    KeyType.ML_DSA_65: "ML-DSA-65",
    KeyType.FALCON_512: "Falcon-512",
}

# Raw byte lengths the ledger expects. Checked at construction so a wrong-length
# key fails here, naming the lengths, rather than at a node as 1220.
_SIZES = {
    KeyType.ML_DSA_65: (1952, 4032),
    KeyType.FALCON_512: (897, 1281),
}


class KeyPair:
    """A post-quantum key pair that interoperates with Activeledger.

    Keys are base64 of the raw algorithm bytes, matching the JavaScript SDK's
    on-disk format. That format names the field ``pkcs8pem``, which is a
    historical lie for everything except RSA and is kept because changing it
    would break every exported key.
    """

    def __init__(
        self,
        key_type: KeyType,
        public_bytes: bytes,
        private_bytes: Optional[bytes] = None,
    ) -> None:
        if key_type not in _MECHANISM:
            raise ValueError(
                f"{key_type} is not a post-quantum type; "
                f"expected one of {', '.join(k.value for k in _MECHANISM)}"
            )
        want_public, want_private = _SIZES[key_type]
        if len(public_bytes) != want_public:
            raise ValueError(
                f"{key_type.value} public key should be {want_public} bytes, "
                f"got {len(public_bytes)}"
            )
        if private_bytes is not None and len(private_bytes) != want_private:
            raise ValueError(
                f"{key_type.value} private key should be {want_private} bytes, "
                f"got {len(private_bytes)}"
            )
        self._key_type = key_type
        self._public = public_bytes
        self._private = private_bytes

    # -- construction ----------------------------------------------------

    @classmethod
    def generate(cls, key_type: KeyType) -> "KeyPair":
        oqs = _oqs()
        with oqs.Signature(_MECHANISM[key_type]) as signer:
            public = signer.generate_keypair()
            private = signer.export_secret_key()
        return cls(key_type, public, private)

    @classmethod
    def from_keys(cls, key_type: KeyType, public_b64: str, private_b64: str) -> "KeyPair":
        return cls(key_type, _decode(public_b64, "public"), _decode(private_b64, "private"))

    @classmethod
    def from_public(cls, key_type: KeyType, public_b64: str) -> "KeyPair":
        """A verify-only key pair."""
        return cls(key_type, _decode(public_b64, "public"), None)

    # -- Signer protocol -------------------------------------------------

    @property
    def key_type(self) -> KeyType:
        return self._key_type

    @property
    def public_key(self) -> str:
        return base64.b64encode(self._public).decode("ascii")

    @property
    def private_key_b64(self) -> str:
        if self._private is None:
            raise ValueError("This key pair has no private key - it is verify-only")
        return base64.b64encode(self._private).decode("ascii")

    @property
    def can_sign(self) -> bool:
        return self._private is not None

    def sign(self, message: bytes) -> bytes:
        if self._private is None:
            raise ValueError("This key pair has no private key - it is verify-only")
        oqs = _oqs()
        # Plain sign() calls OQS_SIG_sign, the pure empty-context FIPS 204
        # path - not sign_with_ctx_str, which would produce a signature the
        # ledger cannot verify.
        with oqs.Signature(_MECHANISM[self._key_type], secret_key=self._private) as signer:
            return signer.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify a signature.

        Returns ``False`` rather than raising for malformed input. A caller
        should not have to tell "this signature is invalid" from "this
        signature is the wrong shape" -- both mean the same thing at the call
        site, and making one an exception invites a bare ``except`` that
        swallows the other.
        """
        oqs = _oqs()
        try:
            with oqs.Signature(_MECHANISM[self._key_type]) as verifier:
                return bool(verifier.verify(message, signature, self._public))
        except PostQuantumUnavailable:
            raise
        except Exception:
            return False

    def __repr__(self) -> str:  # no key material in the repr
        half = "public+private" if self.can_sign else "public only"
        return f"<KeyPair {self._key_type.value} {half}>"


def _decode(value: str, what: str) -> bytes:
    # Checked explicitly so None reports what it is rather than being blamed
    # on base64. A key arriving as None from a config file or a database
    # column is a likelier mistake than a malformed one.
    if not isinstance(value, str):
        raise TypeError(f"{what} key must be a string, got {type(value).__name__}")

    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"{what} key is not valid base64") from exc
