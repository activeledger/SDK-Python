"""HTTP connection to an Activeledger node. Standard library only."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from .keys import Signer
from .transaction import Transaction, onboard_transaction

__all__ = ["Connection", "LedgerResponse", "Identity"]


class LedgerResponse:
    """The ledger's reply to a submitted transaction."""

    def __init__(self, raw: str, status: int = 200) -> None:
        self.raw = raw
        self.status = status
        try:
            doc = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            doc = None
        self._doc: Dict[str, Any] = doc if isinstance(doc, dict) else {}
        self._valid = isinstance(doc, dict)

    @property
    def errors(self) -> List[str]:
        """Errors the network reported.

        Non-empty means the transaction did **not** commit, even though the
        HTTP status was 200. The ledger answers 200 for a rejected
        transaction, so treating HTTP success as ledger success is wrong --
        and it is the kind of wrong that looks fine until something important
        silently does not happen.

        A non-2xx status, or a body that is not a JSON object, is also an
        error: nothing here can show the transaction committed. So is a body
        with no ``$summary`` -- every reply the node builds for a finished
        transaction carries one, so its absence means this is not that reply.
        """
        errors: List[str] = []
        if not 200 <= self.status < 300:
            errors.append(f"HTTP {self.status}")
        if not self._valid:
            errors.append("Response body is not a JSON object")
        summary = self._doc.get("$summary")
        if self._valid and summary is None:
            errors.append("Response has no $summary")
        elif summary is not None and not isinstance(summary, dict):
            errors.append("Response $summary is not a JSON object")
        elif summary:
            reported = summary.get("errors") or []
            errors.extend(reported if isinstance(reported, list) else [str(reported)])
        return errors

    @property
    def committed(self) -> bool:
        return not self.errors

    @property
    def new_streams(self) -> List[str]:
        streams = self._doc.get("$streams")
        created = streams.get("new") if isinstance(streams, dict) else None
        if not isinstance(created, list):
            return []
        return [e.get("id") for e in created if isinstance(e, dict) and e.get("id")]

    @property
    def responses(self) -> List[Any]:
        """Values contracts returned via ``returnToRemote``."""
        responses = self._doc.get("$responses")
        return list(responses) if isinstance(responses, list) else []

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
        status, text = self._post("/", body)
        return LedgerResponse(text, status)

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

    def _post(self, path: str, body: str) -> Tuple[int, str]:
        request = urllib.request.Request(
            self.base_url + path,
            data=body.encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # A ledger rejection is a 200 with errors in the body, so an
            # HTTPError is a transport or routing problem. The body is kept,
            # but the status travels with it so the response cannot look
            # committed.
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def _get(self, path: str) -> Tuple[int, str]:
        request = urllib.request.Request(self.base_url + path, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
