"""The package's lazy attributes, the secp256k1 missing-extra guard and a
canonical-JSON corner."""

import subprocess
import sys
import textwrap

import pytest

import activeledger
from activeledger.canonical import canonical_json, js_number


# -- __init__ lazy attributes ----------------------------------------------------

def test_unknown_attribute_raises_attributeerror_naming_the_module():
    with pytest.raises(AttributeError, match=r"module 'activeledger' has no attribute 'Nope'"):
        activeledger.Nope


def test_hasattr_is_false_for_unknown_names():
    assert not hasattr(activeledger, "KeyPairs")


def test_secp256k1_keypair_resolves_to_the_ec_module():
    from activeledger import ec

    assert activeledger.Secp256k1KeyPair is ec.Secp256k1KeyPair


def test_pq_names_resolve_to_the_pq_module():
    from activeledger import pq

    assert activeledger.KeyPair is pq.KeyPair
    assert activeledger.PostQuantumUnavailable is pq.PostQuantumUnavailable


def test_every_name_in_all_resolves():
    for name in activeledger.__all__:
        assert getattr(activeledger, name) is not None, name


def test_lazy_attributes_do_not_import_the_extras_until_asked():
    program = textwrap.dedent(
        """
        import sys
        import activeledger
        assert "oqs" not in sys.modules and "ecdsa" not in sys.modules
        assert "activeledger.pq" not in sys.modules and "activeledger.ec" not in sys.modules
        activeledger.PostQuantumUnavailable
        assert "activeledger.pq" in sys.modules and "activeledger.ec" not in sys.modules
        print("OK")
        """
    )
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# -- ec.py without python-ecdsa --------------------------------------------------------

def _run_without_ecdsa(body: str) -> subprocess.CompletedProcess:
    blocker = textwrap.dedent(
        """
        import sys

        class _Blocker:
            def find_spec(self, name, path=None, target=None):
                if name == "ecdsa" or name.startswith("ecdsa."):
                    raise ImportError("ecdsa is not installed (blocked for this test)")
                return None

        sys.meta_path.insert(0, _Blocker())
        for _name in [m for m in sys.modules if m == "ecdsa" or m.startswith("ecdsa.")]:
            del sys.modules[_name]
        """
    )
    return subprocess.run(
        [sys.executable, "-c", blocker + textwrap.dedent(body)],
        capture_output=True, text=True, timeout=120,
    )


@pytest.mark.parametrize(
    "call",
    [
        "Secp256k1KeyPair.from_seed(b'\\x01' * 32)",
        "Secp256k1KeyPair.from_phrase('abandon ' * 11 + 'about')",
        "Secp256k1KeyPair.from_public_key('0x' + '02' + '11' * 32)",
        "is_high_s(b'\\x30\\x06\\x02\\x01\\x01\\x02\\x01\\x01')",
    ],
)
def test_every_ec_entry_point_names_the_extra_when_ecdsa_is_absent(call):
    result = _run_without_ecdsa(
        f"""
        from activeledger.ec import Secp256k1KeyPair, is_high_s
        try:
            {call}
        except ImportError as exc:
            assert "activeledger[ec]" in str(exc), str(exc)
            print("OK")
        else:
            raise AssertionError("expected ImportError")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_the_ec_module_itself_imports_without_ecdsa():
    result = _run_without_ecdsa(
        """
        import activeledger.ec as ec
        assert ec._AVAILABLE is False
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


# -- canonical -0.0 -----------------------------------------------------------------------

def test_negative_zero_is_zero_like_javascript():
    assert js_number(-0.0) == "0"
    assert canonical_json({"n": -0.0}) == '{"n":0}'
    assert canonical_json([-0.0, 0.0, 0]) == "[0,0,0]"
