"""Building and signing transactions."""

from __future__ import annotations

import base64
from typing import Any, Dict, Mapping, Optional

from .canonical import canonical_bytes, canonical_json
from .keys import KeyType, Signer

__all__ = ["Transaction", "TransactionBuilder", "onboard_transaction"]


class Transaction:
    """A signed transaction, ready to submit.

    ``body`` is the ``$tx`` object. ``sigs`` maps a signer label to a base64
    signature over **the canonical bytes of body and nothing else** -- not the
    envelope, not a hash of it, not a length-prefixed form.
    """

    def __init__(self, body: Dict[str, Any], sigs: Dict[str, str], self_sign: bool = False) -> None:
        self.body = body
        self.sigs = sigs
        self.self_sign = self_sign

    def envelope(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"$tx": self.body}
        if self.self_sign:
            out["$selfsign"] = True
        out["$sigs"] = self.sigs
        return out

    def to_json(self) -> str:
        return canonical_json(self.envelope())

    def signed_bytes(self) -> bytes:
        """The exact bytes that were signed. Useful when debugging a 1220."""
        return canonical_bytes(self.body)


def onboard_transaction(signer: Signer, label: str = "identity") -> Transaction:
    """Build the onboarding transaction for a new identity.

    Two things here are the most common first failure in any port, so they
    happen in one place rather than being left to a caller:

    * ``$selfsign`` is true and ``$sigs`` is keyed by the ``$i`` **label**
      (``"identity"``), not by a stream id. There is no stream yet.
    * ``type`` is always present. The ledger defaults a missing type to
      ``"rsa"`` and then attempts RSA verification against a base64
      post-quantum blob, returning 1220 "Signature Incorrect" with nothing
      said about key types.
    """
    body: Dict[str, Any] = {
        "$namespace": "default",
        "$contract": "onboard",
        "$i": {
            label: {
                "type": signer.key_type.value,
                "publicKey": signer.public_key,
            }
        },
        "$o": {},
    }
    signature = base64.b64encode(signer.sign(canonical_bytes(body))).decode("ascii")
    return Transaction(body, {label: signature}, self_sign=True)


class TransactionBuilder:
    """Builds an ordinary transaction.

    Insertion order is preserved throughout, because the ledger does not
    canonicalise key order and the signature covers the order actually
    written.
    """

    def __init__(self) -> None:
        self._namespace: Optional[str] = None
        self._contract: Optional[str] = None
        self._entry: Optional[str] = None
        self._inputs: Dict[str, Any] = {}
        self._outputs: Dict[str, Any] = {}
        self._readonly: Dict[str, str] = {}
        self._signers: Dict[str, Signer] = {}

    def namespace(self, value: str) -> "TransactionBuilder":
        self._namespace = value
        return self

    def contract(self, value: str) -> "TransactionBuilder":
        self._contract = value
        return self

    def entry(self, value: str) -> "TransactionBuilder":
        self._entry = value
        return self

    def input(
        self,
        stream_id: str,
        signer: Signer,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> "TransactionBuilder":
        """Add an input stream, its signing key, and any payload fields."""
        self._inputs[stream_id] = dict(payload or {})
        self._signers[stream_id] = signer
        return self

    def output(
        self, stream_id: str, payload: Optional[Mapping[str, Any]] = None
    ) -> "TransactionBuilder":
        self._outputs[stream_id] = dict(payload or {})
        return self

    def readonly(self, label: str, stream_id: str) -> "TransactionBuilder":
        """Add a stream to ``$r``, the read-only set.

        This is how state is read from Activeledger. There is no separate read
        API: a node's storage service listens only on its own host, so reading
        is a transaction like anything else. The contract receives the named
        streams and hands values back with ``returnToRemote``, which arrive in
        :attr:`LedgerResponse.responses`.
        """
        self._readonly[label] = stream_id
        return self

    def build(self) -> Transaction:
        if self._namespace is None:
            raise ValueError("namespace is required")
        if self._contract is None:
            raise ValueError("contract is required")
        if not self._signers:
            raise ValueError("at least one input with a signing key is required")

        body: Dict[str, Any] = {}
        if self._entry is not None:
            body["$entry"] = self._entry
        body["$namespace"] = self._namespace
        body["$contract"] = self._contract
        body["$i"] = self._inputs
        if self._outputs:
            body["$o"] = self._outputs
        if self._readonly:
            body["$r"] = self._readonly

        message = canonical_bytes(body)
        sigs = {
            label: base64.b64encode(signer.sign(message)).decode("ascii")
            for label, signer in self._signers.items()
        }
        return Transaction(body, sigs, self_sign=False)
