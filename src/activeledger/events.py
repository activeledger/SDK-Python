"""Server-sent event subscription. Standard library only.

The SSE framing rules that matter here are few and specific, and getting any
of them wrong is a bug that only shows up under real traffic:

* multiple ``data:`` lines in one event concatenate with newlines -- treating
  them as separate events is the classic SSE parsing bug
* a line starting ``:`` is a comment, used as a heartbeat, and emitting those
  as events delivers a stream of empty payloads
* ``event:`` and ``id:`` apply to the event being accumulated and must not
  leak into the next one
* a blank line dispatches
"""

from __future__ import annotations

import urllib.request
from typing import Iterator, NamedTuple, Optional

__all__ = ["LedgerEvent", "EventStream"]


class LedgerEvent(NamedTuple):
    """One server-sent event."""

    name: Optional[str]
    data: str
    id: Optional[str]


class EventStream:
    """Subscribes to a node's event stream.

    A generator, so leaving the loop closes the connection::

        for event in ledger.events.subscribe():
            print(event.data)
            if done:
                break     # connection closes here

    That is the reason it is a generator and not a callback API: with
    callbacks, closing is the caller's job and the thing they forget, and the
    symptom is a node holding open connections for subscribers that are gone.
    """

    def __init__(self, base_url: str, timeout: Optional[float] = None) -> None:
        self.base_url = base_url.rstrip("/")
        # No default read timeout. Event streams are long-lived by design and
        # a timeout would close them mid-subscription for being quiet.
        self.timeout = timeout

    def subscribe(self, path: str = "/events") -> Iterator[LedgerEvent]:
        request = urllib.request.Request(
            self.base_url + path,
            headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
            method="GET",
        )
        kwargs = {"timeout": self.timeout} if self.timeout is not None else {}
        response = urllib.request.urlopen(request, **kwargs)  # noqa: S310
        try:
            name: Optional[str] = None
            event_id: Optional[str] = None
            data: list[str] = []

            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")

                if not line:
                    if data:
                        yield LedgerEvent(name, "\n".join(data), event_id)
                        data = []
                        name = None
                        event_id = None
                    continue

                if line.startswith(":"):
                    # Comment or heartbeat. Ignored deliberately.
                    continue
                if line.startswith("event:"):
                    name = line[len("event:"):].strip()
                elif line.startswith("id:"):
                    event_id = line[len("id:"):].strip()
                elif line.startswith("data:"):
                    data.append(line[len("data:"):].strip())

            # A stream that ends without a trailing blank line still has a
            # complete event pending.
            if data:
                yield LedgerEvent(name, "\n".join(data), event_id)
        finally:
            response.close()
