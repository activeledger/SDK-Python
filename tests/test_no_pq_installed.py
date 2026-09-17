"""The core must work with liboqs absent.

This is the test that keeps the packaging promise honest, and the one most
likely to rot silently: everything else in this suite runs in an environment
where the [pq] extra happens to be installed, so nothing else would notice the
core growing a hard dependency on it.

Run in a subprocess with `oqs` blocked from import, so it fails the way a user
without a C toolchain would experience it rather than the way a mock does.
"""

import subprocess
import sys
import textwrap

BLOCK_OQS = textwrap.dedent(
    """
    import sys

    class _Blocker:
        def find_module(self, name, path=None):
            if name == "oqs" or name.startswith("oqs."):
                return self
            return None
        def load_module(self, name):
            raise ImportError("liboqs is not installed (blocked for this test)")
        def find_spec(self, name, path=None, target=None):
            if name == "oqs" or name.startswith("oqs."):
                raise ImportError("liboqs is not installed (blocked for this test)")
            return None

    sys.meta_path.insert(0, _Blocker())
    sys.modules.pop("oqs", None)
    """
)


def _run(body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", BLOCK_OQS + textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_core_imports_without_liboqs():
    result = _run(
        """
        import activeledger
        print("OK", activeledger.__version__)
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_canonical_json_works_without_liboqs():
    result = _run(
        """
        from activeledger import canonical_json
        assert canonical_json({"b": 1.0, "a": "caf\\u00e9"}) == '{"b":1,"a":"caf\\u00e9"}'
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_transactions_build_and_sign_without_liboqs():
    # An application signing elsewhere - an HSM, a remote service, a user's
    # wallet - never needs the extra at all.
    result = _run(
        """
        from activeledger import KeyType, TransactionBuilder

        class ExternalSigner:
            key_type = KeyType.ML_DSA_65
            public_key_b64 = "PUB"
            def sign(self, message):
                return b"signed-elsewhere"

        tx = (TransactionBuilder().namespace("n").contract("c")
              .input("stream", ExternalSigner()).build())
        assert tx.sigs
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_asking_for_a_pq_key_names_the_extra():
    # The failure mode is part of the design: a message naming the extra, not
    # a CMake traceback from inside a dependency.
    result = _run(
        """
        from activeledger import KeyPair, KeyType
        try:
            KeyPair.generate(KeyType.ML_DSA_65)
        except ImportError as exc:
            assert "activeledger-sdk[pq]" in str(exc), str(exc)
            print("OK")
        else:
            raise AssertionError("expected ImportError")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_events_and_connection_import_without_liboqs():
    result = _run(
        """
        from activeledger import Activeledger, Connection, EventStream
        Activeledger("http://localhost:1")
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
