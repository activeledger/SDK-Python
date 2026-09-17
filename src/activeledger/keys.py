"""Key types and the signer protocol.

The key type strings here are the whole contract with the ledger. It validates
nothing else about them: the value travels from ``$tx.$i[label].type`` through
``Stream.setAuthority``, which does no checking at all, is stored verbatim on
``meta.authorities[].type``, and comes back out at verification time.

Two consequences shape this module:

* A typo in the string, or a key of the wrong length, surfaces as **1220
  "Signature Incorrect"** -- never as "unknown algorithm". Validate locally or
  spend an afternoon on the wrong thing.
* **The ledger defaults a missing type to** ``"rsa"``. Omit it for a
  post-quantum key and it attempts RSA verification against a base64 blob. So
  this SDK always sends the type explicitly and never relies on a default.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

__all__ = ["KeyType", "Signer", "PQ_EXTRA_HINT"]


PQ_EXTRA_HINT = (
    "Post-quantum support needs the optional extra:\n"
    "    pip install 'activeledger-sdk[pq]'\n"
    "It pulls in liboqs-python, which builds liboqs from source on first "
    "import and needs git, CMake, a C compiler and OpenSSL headers. The core "
    "SDK deliberately does not require any of that, so transaction building, "
    "submission and events work without it."
)


class KeyType(str, Enum):
    """Key types the ledger understands, with their exact wire strings.

    A ``str`` enum so ``KeyType.ML_DSA_65 == "ml-dsa-65"`` holds and the value
    serialises straight into a transaction without conversion.
    """

    RSA = "rsa"
    SECP256K1 = "secp256k1"
    ML_DSA_65 = "ml-dsa-65"
    FALCON_512 = "falcon-512"

    @property
    def is_post_quantum(self) -> bool:
        return self in (KeyType.ML_DSA_65, KeyType.FALCON_512)

    def __str__(self) -> str:  # so f-strings give the wire value
        return self.value


@runtime_checkable
class Signer(Protocol):
    """Anything that can sign transaction bytes and name its key type.

    A protocol rather than a base class so a caller can sign elsewhere -- an
    HSM, a remote signing service, a key held in a user's wallet -- without
    this SDK needing to know about it, and without installing the ``[pq]``
    extra at all.
    """

    @property
    def key_type(self) -> KeyType:
        ...

    @property
    def public_key_b64(self) -> str:
        ...

    def sign(self, message: bytes) -> bytes:
        ...
