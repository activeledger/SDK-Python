#!/usr/bin/env python3
"""Smoke test of the built wheel, end to end, with no external network.

    python scripts/smoke_wheel.py [--find-links DIR] [--require-all]

Builds the wheel from a copy of the source tree, installs it into a fresh
virtualenv, then runs a script *from that venv* (isolated mode, so the source
tree cannot shadow the installed package) which:

* imports the package and checks it came from the venv's site-packages;
* generates every key type whose extra is installed, builds and signs an
  onboarding and an ordinary transaction with each, and verifies them;
* drives ``Connection`` against an in-process loopback HTTP server that
  answers once with a committed reply and once with a rejected HTTP 200.

Installing needs no network: the wheel has no dependencies. The optional
extras (``ecdsa``, ``liboqs-python``) are installed only if ``--find-links``
points at a directory holding their wheels, and key types whose extra is
missing are reported as not exercised. ``--require-all`` makes that a failure.
liboqs-python also needs liboqs itself, e.g. ``OQS_INSTALL_PATH`` and
``LD_LIBRARY_PATH`` pointing at an existing build; they are inherited.

Not part of the pytest run: it builds and installs, so it is slow.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Run inside the venv, in isolated mode. Kept as text so the venv's
# interpreter, not this one, imports the installed wheel.
INNER = r'''
import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# A system proxy must not intercept the loopback server.
for _var in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
    os.environ.pop(_var, None)
os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1"

import activeledger
from activeledger import (Connection, KeyType, TransactionBuilder,
                          canonical_bytes, onboard_transaction, recovery)

REQUIRE_ALL = sys.argv[1] == "1"
failures = []


def check(condition, what):
    print(("ok   " if condition else "FAIL ") + what)
    if not condition:
        failures.append(what)


# -- the installed package, not the source tree --------------------------------
check("site-packages" in activeledger.__file__, f"imported from the venv ({activeledger.__file__})")
check(len(recovery._wordlist()) == 2048, "bundled BIP-39 wordlist is in the wheel")
check(canonical_bytes({"b": 1.0, "a": "é"}) == '{"b":1,"a":"é"}'.encode(), "canonical bytes")

# -- every key type that is installed ------------------------------------------
signers = {}
try:
    signers["secp256k1"] = activeledger.Secp256k1KeyPair.generate()
except ImportError as exc:
    print("skip secp256k1:", str(exc).splitlines()[0])
for key_type in (KeyType.ML_DSA_65, KeyType.FALCON_512):
    try:
        signers[key_type.value] = activeledger.KeyPair.generate(key_type)
    except ImportError as exc:
        print(f"skip {key_type.value}:", str(exc).splitlines()[0])
check(not (REQUIRE_ALL and len(signers) < 3), f"all key types available (have {sorted(signers)})")

for name, key in signers.items():
    onboard = onboard_transaction(key, "identity")
    check(key.verify(onboard.signed_bytes(), base64.b64decode(onboard.sigs["identity"])),
          f"{name}: onboarding signature verifies")
    check(onboard.self_sign and onboard.body["$i"]["identity"]["type"] == name,
          f"{name}: onboarding names its key type")

    tx = (TransactionBuilder().namespace("smoke").contract("noop")
          .input("stream-1", key, {"n": 1}).output("stream-1", {"ok": True}).build())
    sig = base64.b64decode(tx.sigs["stream-1"])
    check(key.verify(tx.signed_bytes(), sig), f"{name}: transaction signature verifies")
    check(not key.verify(tx.signed_bytes() + b" ", sig), f"{name}: tampered message is rejected")
    check(json.loads(tx.to_json())["$tx"] == tx.body, f"{name}: envelope round-trips")

# -- Connection against a loopback ledger --------------------------------------
seen = []
replies = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8")
        seen.append((self.path, self.headers["Content-Type"], body))
        payload = replies.pop(0).encode()
        self.send_response(200)  # a rejection is HTTP 200 too
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


httpd = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
conn = Connection(f"http://127.0.0.1:{httpd.server_address[1]}", timeout=10)

stub = next(iter(signers.values()), None)
if stub is None:
    class Stub:  # signs elsewhere; needs no extra at all
        key_type = KeyType.ML_DSA_65
        public_key = "PUB"
        def sign(self, message):
            return b"signed-elsewhere"
    stub = Stub()
tx = (TransactionBuilder().namespace("smoke").contract("noop").input("s", stub).build())

replies.append(json.dumps({"$summary": {"commit": 1, "errors": []},
                           "$streams": {"new": [{"id": "abc123"}]}, "$responses": [42]}))
committed = conn.submit(tx)
check(seen[0][0] == "/" and seen[0][2] == tx.to_json(), "committed: exact signed JSON posted to /")
check(seen[0][1].startswith("application/json"), "committed: JSON content type")
check(committed.committed and committed.new_streams == ["abc123"] and committed.responses == [42],
      "committed reply parsed")

replies.append(json.dumps({"$summary": {"commit": 0, "errors": ["1220 Signature Incorrect"]}}))
rejected = conn.submit(tx)
check(not rejected.committed and rejected.errors == ["1220 Signature Incorrect"],
      "rejected HTTP 200 reply is not committed")

replies.append(json.dumps({"$streams": {"new": [{"id": "ident-1"}]}}))
identity = conn.onboard(stub, "identity")
check(identity.stream_id == "ident-1", "onboard returns the new identity")
replies.append(json.dumps({"$summary": {"errors": ["nope"]}}))
try:
    conn.onboard(stub, "identity")
    check(False, "rejected onboard raises")
except RuntimeError:
    check(True, "rejected onboard raises")

httpd.shutdown()
httpd.server_close()
check(not replies, "every scripted reply was consumed")

print(f"\n{'FAILED: ' + str(len(failures)) if failures else 'smoke test passed'}")
sys.exit(1 if failures else 0)
'''


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def build_wheel(source: Path, out: Path) -> Path:
    try:
        run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", out, source])
    except (subprocess.CalledProcessError, OSError):
        # No `build` module: pip can drive setuptools directly.
        run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
             "--wheel-dir", out, source])
    wheels = sorted(out.glob("activeledger-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected one wheel in {out}, found {wheels}")
    return wheels[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--find-links", type=Path,
                        help="directory of wheels for the ecdsa / liboqs-python extras (offline)")
    parser.add_argument("--require-all", action="store_true",
                        help="fail unless secp256k1, ml-dsa-65 and falcon-512 were all exercised")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="activeledger-smoke-") as tmp_name:
        tmp = Path(tmp_name)

        # Build from a copy so the repo gains no build/ or *.egg-info.
        source = tmp / "src-copy"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            if (ROOT / name).exists():
                shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "src", source / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        wheel = build_wheel(source, tmp / "dist")

        env_dir = tmp / "venv"
        run([sys.executable, "-m", "venv", env_dir])
        python = env_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

        offline = ["--no-index", "--disable-pip-version-check"]
        run([python, "-m", "pip", "install", *offline, wheel])
        if args.find_links:
            # Extras are best effort: a missing one is reported, not fatal,
            # unless --require-all.
            for extra in ("ecdsa>=0.19", "liboqs-python>=0.16.0"):
                subprocess.run([str(python), "-m", "pip", "install", *offline,
                                "--find-links", str(args.find_links), extra])

        script = tmp / "inner.py"
        script.write_text(INNER, encoding="utf-8")
        # -I: no PYTHON* variables and no cwd on sys.path, so only the
        # installed wheel can satisfy `import activeledger`.
        result = subprocess.run([str(python), "-I", str(script), "1" if args.require_all else "0"],
                                cwd=tmp)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
