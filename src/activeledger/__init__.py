"""Python SDK for Activeledger, with post-quantum identity support.

The core is stdlib-only. Post-quantum keys need the optional extra::

    pip install 'activeledger-sdk[pq]'

Everything else -- canonical JSON, transaction building, submission and event
subscription -- works with no compiled dependency at all, so an application
that signs elsewhere (an HSM, a remote service, a user's wallet) never needs a
C toolchain.

    from activeledger import Activeledger, KeyPair, KeyType

    ledger = Activeledger("http://localhost:5260")
    identity = ledger.onboard(KeyPair.generate(KeyType.ML_DSA_65))
"""

from .canonical import canonical_bytes, canonical_json
from .connection import Connection, Identity, LedgerResponse
from .events import EventStream, LedgerEvent
from .keys import KeyType, Signer
from .transaction import Transaction, TransactionBuilder, onboard_transaction

__all__ = [
    "Activeledger",
    "Connection",
    "EventStream",
    "Identity",
    "KeyType",
    "LedgerEvent",
    "LedgerResponse",
    "Signer",
    "Transaction",
    "TransactionBuilder",
    "canonical_bytes",
    "canonical_json",
    "onboard_transaction",
    "KeyPair",
    "PostQuantumUnavailable",
]

__version__ = "1.0.0"


class Activeledger:
    """Entry point.

    There is deliberately no storage endpoint here. A node's storage service
    listens only on the node's own host, so it is not something a client can
    reach. State is read through a transaction: name streams in ``$r`` with
    :meth:`TransactionBuilder.readonly` and have the contract return values
    with ``returnToRemote``, which arrive in ``LedgerResponse.responses``.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.connection = Connection(base_url, timeout=timeout)
        self.events = EventStream(base_url)

    def onboard(self, signer, label: str = "identity") -> Identity:
        return self.connection.onboard(signer, label)

    def submit(self, transaction: Transaction) -> LedgerResponse:
        return self.connection.submit(transaction)

    @staticmethod
    def transaction() -> TransactionBuilder:
        return TransactionBuilder()


def __getattr__(name):
    """Expose KeyPair lazily so importing this package never needs liboqs.

    `from activeledger import KeyPair` works whether or not the [pq] extra is
    installed; it is only actually using one that raises, and with a message
    naming the extra rather than a CMake traceback.
    """
    if name in ("KeyPair", "PostQuantumUnavailable"):
        from . import pq

        return getattr(pq, name)

    # Same reasoning for secp256k1: importing this package must not require
    # the [ec] extra either, and a caller who never touches secp256k1 should
    # never be asked to install python-ecdsa.
    if name == "Secp256k1KeyPair":
        from . import ec

        return ec.Secp256k1KeyPair

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
