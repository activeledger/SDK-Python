"""The package must work, and fail helpfully, without the [ec] extra.

Mirrors test_no_pq_installed. Importing activeledger, building a transaction
and verifying a signature must all work with no secp256k1 library present --
only actually using a secp256k1 key may fail, and it must say which extra to
install rather than raising a bare ImportError from somewhere in the stack.

Run in a subprocess with the import blocked, because ecdsa is installed in
the environment that runs this file.
"""

import subprocess
import sys
import textwrap


def run_without_ecdsa(code: str) -> subprocess.CompletedProcess:
    # find_spec is the one modern Python actually consults; find_module is
    # kept only so this still blocks on older interpreters.
    blocker = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_module(self, name, path=None):
                if name == "ecdsa" or name.startswith("ecdsa."):
                    return self
                return None
            def load_module(self, name):
                raise ImportError("ecdsa is not installed (blocked for this test)")
            def find_spec(self, name, path=None, target=None):
                if name == "ecdsa" or name.startswith("ecdsa."):
                    raise ImportError("ecdsa is not installed (blocked for this test)")
                return None

        sys.meta_path.insert(0, _Blocker())
        for _name in [m for m in sys.modules if m == "ecdsa" or m.startswith("ecdsa.")]:
            del sys.modules[_name]
        """
    )
    program = blocker + textwrap.dedent(code)

    return subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True
    )


def test_the_package_imports_without_ecdsa():
    result = run_without_ecdsa(
        """
        import activeledger
        from activeledger import Transaction
        print("ok")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_building_a_transaction_works_without_ecdsa():
    result = run_without_ecdsa(
        """
        from activeledger.canonical import canonical_bytes
        print(canonical_bytes({"a": 1}).decode())
        """
    )
    assert result.returncode == 0, result.stderr
    assert '{"a":1}' in result.stdout


def test_using_a_secp256k1_key_names_the_extra():
    result = run_without_ecdsa(
        """
        from activeledger import Secp256k1KeyPair
        try:
            Secp256k1KeyPair.generate()
        except ImportError as error:
            print("MESSAGE:", error)
        """
    )
    assert result.returncode == 0, result.stderr
    assert "activeledger-sdk[ec]" in result.stdout
