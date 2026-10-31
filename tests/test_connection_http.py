"""Connection and Activeledger over HTTP, against a stdlib http.server fake.

Covers the wire behaviour test_connection_events does not: the request that
is actually sent, HTTP error statuses, and a successful onboarding.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("ecdsa", reason="needs the [ec] extra")

import activeledger  # noqa: E402
from activeledger import Activeledger, Secp256k1KeyPair  # noqa: E402
from activeledger.canonical import canonical_bytes  # noqa: E402
from activeledger.connection import Connection, Identity, LedgerResponse  # noqa: E402
from activeledger.transaction import onboard_transaction  # noqa: E402

# Activeledger() builds an EventStream, which is deprecated.
pytestmark = pytest.mark.filterwarnings(
    "ignore:EventStream is deprecated:DeprecationWarning"
)


class _Handler(BaseHTTPRequestHandler):
    status = 200
    body = "{}"
    requests = []

    def log_message(self, *args):
        pass

    def _reply(self):
        payload = _Handler.body.encode()
        self.send_response(_Handler.status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        _Handler.requests.append(
            ("POST", self.path, self.headers.get("Content-Type"),
             self.rfile.read(length).decode("utf-8"))
        )
        self._reply()

    def do_GET(self):
        _Handler.requests.append(("GET", self.path, None, ""))
        self._reply()


@pytest.fixture
def server():
    _Handler.status = 200
    _Handler.body = "{}"
    _Handler.requests = []
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


# -- the request that goes on the wire -----------------------------------------

def test_submit_posts_the_exact_signed_json_to_the_root(server):
    key = Secp256k1KeyPair.generate()
    transaction = onboard_transaction(key)

    Connection(server).submit(transaction)

    method, path, content_type, body = _Handler.requests[0]
    assert (method, path) == ("POST", "/")
    assert content_type == "application/json; charset=utf-8"
    assert body == transaction.to_json()


def test_non_ascii_bodies_are_sent_as_utf8(server):
    Connection(server).submit_raw('{"s":"café ☕"}')

    assert _Handler.requests[0][3] == '{"s":"café ☕"}'


def test_trailing_slashes_on_the_base_url_are_stripped(server):
    connection = Connection(server + "///")

    assert connection.base_url == server
    connection.submit_raw("{}")
    assert _Handler.requests[0][1] == "/"


def test_get_returns_the_body_and_requests_the_path(server):
    _Handler.body = "hello"

    assert Connection(server)._get("/api/x") == (200, "hello")
    assert _Handler.requests[0][:2] == ("GET", "/api/x")


def test_an_http_error_surfaces_the_body_not_an_exception(server):
    # The body matters more than the status: it is what names the problem.
    _Handler.status = 500
    _Handler.body = json.dumps({"$summary": {"errors": ["node exploded"]}})

    response = Connection(server).submit_raw("{}")

    assert response.errors == ["HTTP 500", "node exploded"]
    assert response.committed is False


def test_a_non_json_error_page_is_kept_raw(server):
    _Handler.status = 404
    _Handler.body = "<html>Not Found</html>"

    response = Connection(server).submit_raw("{}")

    assert response.raw == "<html>Not Found</html>"
    assert response.errors == ["HTTP 404", "Response body is not a JSON object"]
    assert response.committed is False


@pytest.mark.parametrize("body", ["", "<html>Bad Gateway</html>", "{}"])
def test_a_5xx_never_looks_committed(server, body):
    _Handler.status = 502
    _Handler.body = body

    response = Connection(server).submit_raw("{}")

    assert response.committed is False
    assert response.errors[0] == "HTTP 502"


def test_a_ledger_rejection_at_http_200_still_reports_its_errors(server):
    _Handler.body = json.dumps({"$summary": {"errors": ["1220"]}})

    response = Connection(server).submit_raw("{}")

    assert response.errors == ["1220"]
    assert response.committed is False


def test_a_2xx_object_body_without_a_summary_is_not_committed(server):
    _Handler.status = 201
    _Handler.body = "{}"

    response = Connection(server).submit_raw("{}")

    assert response.committed is False
    assert response.errors == ["Response has no $summary"]


def test_a_2xx_body_with_a_summary_and_no_errors_is_committed(server):
    _Handler.status = 201
    _Handler.body = json.dumps({"$summary": {"errors": []}})

    assert Connection(server).submit_raw("{}").committed is True


def test_get_returns_status_and_body_for_http_errors(server):
    _Handler.status = 503
    _Handler.body = "down"

    assert Connection(server)._get("/") == (503, "down")


def test_an_unreachable_node_raises_rather_than_returning_a_response():
    import urllib.error

    # Port 1 on loopback refuses immediately; nothing is listening.
    with pytest.raises(urllib.error.URLError):
        Connection("http://127.0.0.1:1", timeout=2).submit_raw("{}")


def _one_shot_server(reply, hold=0.0):
    """A raw socket that answers one request with ``reply`` bytes, as sent."""
    import socket
    import time

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)

    def serve():
        conn, _ = listener.accept()
        conn.recv(65536)
        conn.sendall(reply)
        time.sleep(hold)
        conn.close()
        listener.close()

    threading.Thread(target=serve, daemon=True).start()
    return f"http://127.0.0.1:{listener.getsockname()[1]}"


def test_a_reply_cut_off_mid_body_raises_rather_than_returning_a_response():
    import http.client

    url = _one_shot_server(
        b"HTTP/1.1 200 OK\r\nContent-Length: 1000\r\nConnection: close\r\n\r\n"
        b'{"$summary":'
    )
    # A partial body would parse as nothing and read as "not committed"; the
    # dropped connection is the real story. Depending on timing the client sees
    # the short body or the reset that follows it.
    with pytest.raises((http.client.IncompleteRead, ConnectionResetError)):
        Connection(url, timeout=2).submit_raw("{}")


def test_a_node_that_never_answers_times_out_rather_than_hanging():
    url = _one_shot_server(b"", hold=2.0)
    with pytest.raises(OSError):
        Connection(url, timeout=0.2).submit_raw("{}")


# -- onboarding ------------------------------------------------------------------

def test_onboard_returns_an_identity_bound_to_the_new_stream(server):
    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$summary": {"commit": 1}, "$streams": {"new": [{"id": "stream-abc"}]}})

    identity = Connection(server).onboard(key, label="me")

    assert isinstance(identity, Identity)
    assert identity.stream_id == "stream-abc"
    assert identity.signer is key


def test_onboard_sends_a_self_signed_transaction_keyed_by_label(server):
    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$summary": {"commit": 1}, "$streams": {"new": [{"id": "s"}]}})

    Connection(server).onboard(key, label="me")

    sent = json.loads(_Handler.requests[0][3])
    assert sent["$selfsign"] is True
    assert list(sent["$sigs"]) == ["me"]
    assert sent["$tx"]["$i"]["me"]["type"] == "secp256k1"
    assert sent["$tx"]["$i"]["me"]["publicKey"] == key.public_key


def test_onboard_signature_verifies_against_the_body_that_was_sent(server):
    import base64

    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$summary": {"commit": 1}, "$streams": {"new": [{"id": "s"}]}})

    Connection(server).onboard(key)

    sent = json.loads(_Handler.requests[0][3])
    signature = base64.b64decode(sent["$sigs"]["identity"])
    assert key.verify(canonical_bytes(sent["$tx"]), signature)


@pytest.mark.parametrize(
    "status, body, reason",
    [
        (500, {"$streams": {"new": [{"id": "s"}]}}, "HTTP 500"),
        (200, {"$summary": {"errors": ["nope"]}, "$streams": {"new": [{"id": "s"}]}}, "nope"),
        (200, {"$streams": {"new": [{"id": "s"}]}}, "no $summary"),
    ],
)
def test_onboard_raises_when_the_reply_is_not_committed_even_with_a_stream(
    server, status, body, reason
):
    _Handler.status = status
    _Handler.body = json.dumps(body)

    with pytest.raises(RuntimeError, match='Onboarding "me" was not committed') as info:
        Connection(server).onboard(Secp256k1KeyPair.generate(), label="me")

    assert reason in str(info.value)


def test_onboard_raises_when_committed_but_no_stream_was_created(server):
    _Handler.body = json.dumps({"$summary": {"commit": 1}})

    with pytest.raises(RuntimeError, match='Onboarding "identity" created no stream'):
        Connection(server).onboard(Secp256k1KeyPair.generate())


# -- LedgerResponse parsing --------------------------------------------------------

def test_an_empty_body_is_an_uncommitted_nothing():
    response = LedgerResponse("")

    assert response.errors == ["Response body is not a JSON object"]
    assert response.committed is False
    assert response.new_streams == [] and response.responses == []


@pytest.mark.parametrize("raw", ["null", "[]", "[1, 2]", '"text"', "42", "true"])
def test_valid_json_that_is_not_an_object_is_not_committed(raw):
    response = LedgerResponse(raw)

    assert response.errors == ["Response body is not a JSON object"]
    assert response.committed is False
    assert response.new_streams == [] and response.responses == []
    repr(response)


@pytest.mark.parametrize("summary", ["text", [], ["x"], 7, True])
def test_a_non_object_summary_is_an_error_not_an_exception(summary):
    response = LedgerResponse(json.dumps({"$summary": summary}))

    assert response.errors == ["Response $summary is not a JSON object"]
    assert response.committed is False


@pytest.mark.parametrize("streams", ["text", [], ["x"], 7, {"new": "abc"}, {"new": [1, None, "x"]}])
def test_a_non_object_streams_yields_no_new_streams(streams):
    assert LedgerResponse(json.dumps({"$streams": streams})).new_streams == []


def test_a_non_list_responses_is_empty():
    assert LedgerResponse(json.dumps({"$responses": "text"})).responses == []


def test_null_summary_streams_and_responses_are_treated_as_empty():
    response = LedgerResponse(
        json.dumps({"$summary": None, "$streams": None, "$responses": None})
    )

    assert response.errors == ["Response has no $summary"]
    assert response.new_streams == []
    assert response.responses == []
    assert response.committed is False


def test_new_streams_skips_entries_without_an_id():
    response = LedgerResponse(
        json.dumps({"$streams": {"new": [{"id": "a"}, {}, {"id": ""}, {"id": "b"}]}})
    )

    assert response.new_streams == ["a", "b"]


def test_multiple_errors_are_all_reported():
    response = LedgerResponse(json.dumps({"$summary": {"errors": ["one", "two"]}}))

    assert response.errors == ["one", "two"]
    assert response.committed is False


def test_str_is_the_raw_body_and_repr_states_the_outcome():
    raw = json.dumps({"$summary": {"errors": ["bad"]}})
    response = LedgerResponse(raw)

    assert str(response) == raw
    assert "committed=False" in repr(response) and "bad" in repr(response)


def test_identity_repr_truncates_the_stream_id_and_names_the_key_type():
    key = Secp256k1KeyPair.generate()
    text = repr(Identity("0123456789abcdefXYZ", key))

    assert "0123456789ab..." in text and "XYZ" not in text
    assert "secp256k1" in text


# -- the Activeledger entry point ----------------------------------------------------

def test_the_entry_point_passes_url_and_timeout_to_its_parts():
    ledger = Activeledger("http://node:5260/", timeout=7.5)

    assert ledger.connection.base_url == "http://node:5260"
    assert ledger.connection.timeout == 7.5
    assert ledger.events.base_url.rstrip("/") == "http://node:5260"


def test_the_entry_point_submit_and_onboard_go_through_the_connection(server):
    ledger = Activeledger(server)
    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps(
        {"$summary": {"commit": 1}, "$streams": {"new": [{"id": "sid"}]}}
    )

    assert ledger.onboard(key).stream_id == "sid"
    response = ledger.submit(onboard_transaction(key))

    assert response.new_streams == ["sid"]
    assert [r[0] for r in _Handler.requests] == ["POST", "POST"]


def test_the_entry_point_builds_a_fresh_builder_each_time():
    first, second = Activeledger.transaction(), Activeledger.transaction()

    assert isinstance(first, activeledger.TransactionBuilder)
    assert first is not second


# -- lazy attributes -------------------------------------------------------------------

def test_secp256k1_key_pair_is_exposed_lazily_from_the_ec_module():
    from activeledger import ec

    assert activeledger.Secp256k1KeyPair is ec.Secp256k1KeyPair


def test_an_unknown_package_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="no attribute 'Nonsense'"):
        activeledger.Nonsense  # noqa: B018


# An onboarding the ledger did not commit must not produce an Identity, whatever
# else the body carries: an identity that was never created surfaces three calls
# later. Go's Client.Onboard refuses these, and so does the Python Connection.
@pytest.mark.parametrize(
    "status, body",
    [
        (500, {"$summary": {"errors": ["boom"]}, "$streams": {"new": [{"id": "s"}]}}),
        (200, {"$summary": {"errors": ["1220 Signature Incorrect"]},
               "$streams": {"new": [{"id": "s"}]}}),
    ],
)
def test_onboard_raises_when_the_ledger_did_not_commit(server, status, body):
    _Handler.status = status
    _Handler.body = json.dumps(body)

    with pytest.raises(RuntimeError):
        Connection(server).onboard(Secp256k1KeyPair.generate())
