"""HTTP connection to an Activeledger node. Standard library only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .keys import Signer
from .transaction import Transaction, onboard_transaction

__all__ = ["Connection", "LedgerResponse", "Identity"]


class LedgerResponse:
    """The ledger's reply to a submitted transaction."""

    def __init__(self, raw: str) -> None:
        self.raw = raw
        try:
            self._doc: Dict[str, Any] = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self._doc = {}

    @property
    def errors(self) -> List[str]:
        """Errors the network reported.

        Non-empty means the transaction did **not** commit, even though the
        HTTP status was 200. The ledger answers 200 for a rejected
        transaction, so treating HTTP success as ledger success is wrong --
        and it is the kind of wrong that looks fine until something important
        silently does not happen.
        """
        summary = self._doc.get("$summary") or {}
        return list(summary.get("errors") or [])

    @property
    def committed(self) -> bool:
        return not self.errors

    @property
    def new_streams(self) -> List[str]:
        streams = self._doc.get("$streams") or {}
        return [entry.get("id") for entry in (streams.get("new") or []) if entry.get("id")]

    @property
    def responses(self) -> List[Any]:
        """Values contracts returned via ``returnToRemote``."""
        return list(self._doc.get("$responses") or [])

    def __repr__(self) -> str:
        return f"<LedgerResponse committed={self.committed} errors={self.errors}>"

    def __str__(self) -> str:
        return self.raw


class Identity:
    """An onboarded identity: its stream id and the key that controls it."""

    def __init__(self, stream_id: str, signer: Signer) -> None:
        self.stream_id = stream_id
        self.signer = signer

    def __repr__(self) -> str:
        return f"<Identity {self.stream_id[:12]}... {self.signer.key_type.value}>"


class Connection:
    """A connection to one Activeledger node.

    Uses :mod:`urllib` rather than ``requests`` so the core SDK has no
    dependencies at all -- which is the whole point of the optional ``[pq]``
    extra.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def submit(self, transaction: Transaction) -> LedgerResponse:
        return self.submit_raw(transaction.to_json())

    def submit_raw(self, body: str) -> LedgerResponse:
        """Submit a pre-built envelope as raw JSON.

        For envelopes built elsewhere, and for testing rejection paths -- a
        tampered body cannot be expressed through :meth:`submit`, because the
        builder would re-sign it into a valid transaction.
        """
        return LedgerResponse(self._post("/", body))

    def onboard(self, signer: Signer, label: str = "identity") -> Identity:
        """Onboard a new identity and return it.

        Raises if the ledger rejected it, rather than returning an Identity
        with an empty stream id -- an onboarding that silently produced no
        identity is a failure that surfaces three calls later.
        """
        response = self.submit(onboard_transaction(signer, label))
        if not response.new_streams:
            raise RuntimeError(f"Onboard failed: {response.raw}")
        return Identity(response.new_streams[0], signer)

    # -- internals -------------------------------------------------------

    def _post(self, path: str, body: str) -> str:
        request = urllib.request.Request(
            self.base_url + path,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # A ledger rejection is a 200 with errors in the body, so an
            # HTTPError is a transport or routing problem - surfacing the body
            # matters more than the status.
            return exc.read().decode("utf-8", errors="replace")

    def _get(self, path: str) -> str:
        request = urllib.request.Request(self.base_url + path, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")
