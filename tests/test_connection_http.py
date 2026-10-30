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

    assert Connection(server)._get("/api/x") == "hello"
    assert _Handler.requests[0][:2] == ("GET", "/api/x")


def test_an_http_error_surfaces_the_body_not_an_exception(server):
    # The body matters more than the status: it is what names the problem.
    _Handler.status = 500
    _Handler.body = json.dumps({"$summary": {"errors": ["node exploded"]}})

    response = Connection(server).submit_raw("{}")

    assert response.errors == ["node exploded"]
    assert response.committed is False


def test_a_non_json_error_page_is_kept_raw(server):
    _Handler.status = 404
    _Handler.body = "<html>Not Found</html>"

    response = Connection(server).submit_raw("{}")

    assert response.raw == "<html>Not Found</html>"
    assert response.errors == []


def test_get_does_not_swallow_http_errors(server):
    import urllib.error

    _Handler.status = 503
    with pytest.raises(urllib.error.HTTPError):
        Connection(server)._get("/")


def test_an_unreachable_node_raises_rather_than_returning_a_response():
    import urllib.error

    # Port 1 on loopback refuses immediately; nothing is listening.
    with pytest.raises(urllib.error.URLError):
        Connection("http://127.0.0.1:1", timeout=2).submit_raw("{}")


# -- onboarding ------------------------------------------------------------------

def test_onboard_returns_an_identity_bound_to_the_new_stream(server):
    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$streams": {"new": [{"id": "stream-abc"}]}})

    identity = Connection(server).onboard(key, label="me")

    assert isinstance(identity, Identity)
    assert identity.stream_id == "stream-abc"
    assert identity.signer is key


def test_onboard_sends_a_self_signed_transaction_keyed_by_label(server):
    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$streams": {"new": [{"id": "s"}]}})

    Connection(server).onboard(key, label="me")

    sent = json.loads(_Handler.requests[0][3])
    assert sent["$selfsign"] is True
    assert list(sent["$sigs"]) == ["me"]
    assert sent["$tx"]["$i"]["me"]["type"] == "secp256k1"
    assert sent["$tx"]["$i"]["me"]["publicKey"] == key.public_key


def test_onboard_signature_verifies_against_the_body_that_was_sent(server):
    import base64

    key = Secp256k1KeyPair.generate()
    _Handler.body = json.dumps({"$streams": {"new": [{"id": "s"}]}})

    Connection(server).onboard(key)

    sent = json.loads(_Handler.requests[0][3])
    signature = base64.b64decode(sent["$sigs"]["identity"])
    assert key.verify(canonical_bytes(sent["$tx"]), signature)


# -- LedgerResponse parsing --------------------------------------------------------

def test_an_empty_body_is_an_uncommitted_nothing():
    response = LedgerResponse("")

    assert response.errors == [] and response.new_streams == [] and response.responses == []


def test_null_summary_streams_and_responses_are_treated_as_empty():
    response = LedgerResponse(
        json.dumps({"$summary": None, "$streams": None, "$responses": None})
    )

    assert response.errors == []
    assert response.new_streams == []
    assert response.responses == []
    assert response.committed is True


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
    _Handler.body = json.dumps({"$streams": {"new": [{"id": "sid"}]}})

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
