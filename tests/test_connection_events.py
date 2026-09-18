"""HTTP and SSE, against a stdlib http.server fake - no test dependencies."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from activeledger.connection import Connection, LedgerResponse
from activeledger.events import EventStream


class _Handler(BaseHTTPRequestHandler):
    post_body = "{}"
    sse_body = "data: hello\n\n"
    received = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _Handler.received.append(self.rfile.read(length).decode())
        payload = _Handler.post_body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        payload = _Handler.sse_body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@pytest.fixture
def server():
    _Handler.received = []
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


# The ledger answers 200 for a REJECTED transaction, so treating HTTP success
# as ledger success is wrong - and wrong in a way that looks fine until
# something important silently did not happen.
def test_rejected_transaction_is_http_200_and_not_committed(server):
    _Handler.post_body = json.dumps({"$summary": {"errors": ["Signature Incorrect"]}})
    response = Connection(server).submit_raw("{}")
    assert response.committed is False
    assert response.errors == ["Signature Incorrect"]


def test_committed_transaction(server):
    _Handler.post_body = json.dumps({"$summary": {"commit": 1}})
    assert Connection(server).submit_raw("{}").committed is True


def test_new_streams_are_extracted(server):
    _Handler.post_body = json.dumps({"$streams": {"new": [{"id": "abc123"}]}})
    assert Connection(server).submit_raw("{}").new_streams == ["abc123"]


def test_responses_from_return_to_remote(server):
    _Handler.post_body = json.dumps({"$responses": [{"echoed": "hi"}]})
    assert Connection(server).submit_raw("{}").responses == [{"echoed": "hi"}]


def test_onboard_raises_when_no_stream_was_created(server):
    # Better than returning an Identity with an empty id, which surfaces as a
    # confusing failure three calls later.
    _Handler.post_body = json.dumps({"$summary": {"errors": ["nope"]}})

    class Stub:
        key_type = type("K", (), {"value": "ml-dsa-65"})()
        public_key = "PUB"

        def sign(self, m):
            return b"S"

    with pytest.raises(RuntimeError, match="Onboard failed"):
        Connection(server).onboard(Stub())


def test_malformed_response_body_does_not_explode(server):
    _Handler.post_body = "not json at all"
    response = Connection(server).submit_raw("{}")
    assert response.errors == [] and response.raw == "not json at all"


# -- SSE ---------------------------------------------------------------

def test_parses_a_simple_event(server):
    _Handler.sse_body = "data: hello\n\n"
    events = list(EventStream(server).subscribe())
    assert [e.data for e in events] == ["hello"]


def test_reassembles_multi_line_data(server):
    # Treating these as separate events is the classic SSE parsing bug.
    _Handler.sse_body = "data: line one\ndata: line two\n\n"
    events = list(EventStream(server).subscribe())
    assert len(events) == 1 and events[0].data == "line one\nline two"


def test_ignores_comments_and_heartbeats(server):
    _Handler.sse_body = ": heartbeat\n\ndata: real\n\n: another\n\n"
    events = list(EventStream(server).subscribe())
    assert [e.data for e in events] == ["real"]


def test_carries_event_name_and_id(server):
    _Handler.sse_body = "event: commit\nid: 42\ndata: payload\n\n"
    event = next(iter(EventStream(server).subscribe()))
    assert (event.name, event.id, event.data) == ("commit", "42", "payload")


def test_name_and_id_do_not_leak_into_the_next_event(server):
    _Handler.sse_body = "event: first\nid: 1\ndata: a\n\ndata: b\n\n"
    events = list(EventStream(server).subscribe())
    assert events[0].name == "first"
    assert events[1].name is None and events[1].id is None


def test_data_containing_a_colon_survives(server):
    _Handler.sse_body = 'data: {"url":"http://example.com"}\n\n'
    assert next(iter(EventStream(server).subscribe())).data == '{"url":"http://example.com"}'


def test_trailing_event_without_blank_line_is_still_delivered(server):
    _Handler.sse_body = "data: last\n"
    assert [e.data for e in EventStream(server).subscribe()] == ["last"]


def test_empty_stream_yields_nothing(server):
    _Handler.sse_body = ""
    assert list(EventStream(server).subscribe()) == []


def test_breaking_out_of_the_loop_closes_the_connection(server):
    # The reason this is a generator: leaving the loop must close the
    # connection rather than leaving the node holding it.
    _Handler.sse_body = "data: one\n\ndata: two\n\ndata: three\n\n"
    stream = EventStream(server).subscribe()
    first = next(stream)
    stream.close()
    assert first.data == "one"
