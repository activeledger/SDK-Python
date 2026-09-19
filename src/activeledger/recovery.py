"""BIP-39 recovery phrases, and the seed each key type derives from one.

Two layers, and conflating them is the mistake this module is arranged to
prevent. A phrase becomes a 64-byte BIP-39 seed; that seed becomes the seed
the chosen algorithm actually takes. They are different lengths and different
constructions, and :func:`derive_seed` is the step between them.

The derivation::

    BIP-39 seed S = PBKDF2-HMAC-SHA512(phrase, "mnemonic" + passphrase,
                                       2048 iterations, 64 bytes)

    ml-dsa-65   HKDF-SHA512(S, salt="", info="activeledger-seed-v1:ml-dsa-65", 32)
    falcon-512  HKDF-SHA512(S, salt="", info="activeledger-seed-v1:falcon-512", 48)
    secp256k1   HMAC-SHA512("Bitcoin seed", S)[0..32]

``secp256k1`` does not use HKDF, and that is not an oversight. The JavaScript
SDK has shipped ``restoreBIP39Key`` with the construction above since before
the post-quantum types existed, so phrases are already in use. Changing it
would hand every one of those users a different key for a phrase that used to
work -- not an error, just an identity that is no longer theirs. The
post-quantum types are new and carry no such debt, so they get the
construction with proper domain separation.

Published, with cross-language vectors, in the JavaScript SDK's
``vectors/seed-vectors.json``.

Nothing here needs an optional dependency: PBKDF2 is in :mod:`hashlib` and
HKDF is a short HMAC loop, checked byte for byte against node's
``crypto.hkdfSync`` and PHP's ``hash_hkdf``.
"""

from __future__ import annotations

import hashlib
import hmac
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import List

from .keys import KeyType

__all__ = ["to_seed", "derive_seed", "validate", "SEED_SIZES"]

#: BIP-39's fixed PBKDF2 parameters. Not tunable: changing one changes every
#: identity ever derived.
_ITERATIONS = 2048
_BIP39_SEED_SIZE = 64

#: Each algorithm's own seed length. A wrong length is refused, never padded.
SEED_SIZES = {
    KeyType.SECP256K1: 32,
    KeyType.ML_DSA_65: 32,
    KeyType.FALCON_512: 48,
}

_WORDLIST_FILE = Path(__file__).with_name("bip39-english.txt")


@lru_cache(maxsize=1)
def _wordlist() -> List[str]:
    try:
        words = _WORDLIST_FILE.read_text(encoding="utf-8").split()
    except OSError as error:
        raise RuntimeError(f"The BIP-39 wordlist is missing from {_WORDLIST_FILE}") from error

    if len(words) != 2048:
        raise RuntimeError(f"The BIP-39 wordlist should hold 2048 words, found {len(words)}")

    return words


def _nfkd(value: str) -> str:
    """BIP-39 requires NFKD. Only matters for non-ASCII passphrases, but a
    passphrase that normalises differently derives a different seed."""
    return unicodedata.normalize("NFKD", value)


def validate(phrase: str) -> str:
    """Checks a phrase and returns it normalised and single-spaced.

    The checksum is verified, not just the word membership. A mistyped phrase
    that is not checked does not fail: it derives a perfectly valid key for an
    identity nobody owns, and the only symptom is the ledger not recognising
    it.

    :raises ValueError: if the phrase is not a valid mnemonic
    """
    words = _nfkd(phrase).split()

    # 12, 15, 18, 21 and 24 are the only valid lengths.
    if len(words) < 12 or len(words) > 24 or len(words) % 3 != 0:
        raise ValueError(f"a BIP-39 phrase is 12, 15, 18, 21 or 24 words, got {len(words)}")

    wordlist = _wordlist()
    index = {word: position for position, word in enumerate(wordlist)}

    bits = ""
    for position, word in enumerate(words, start=1):
        if word not in index:
            raise ValueError(f'word {position} ("{word}") is not in the BIP-39 English wordlist')
        bits += format(index[word], "011b")

    checksum_bits = len(words) // 3
    entropy_bits = len(bits) - checksum_bits
    entropy = int(bits[:entropy_bits], 2).to_bytes(entropy_bits // 8, "big")
    expected = format(hashlib.sha256(entropy).digest()[0], "08b")[:checksum_bits]

    if bits[entropy_bits:] != expected:
        raise ValueError(
            "the BIP-39 checksum does not match - the phrase has a typo or the words are in "
            "the wrong order. Deriving from it anyway would produce a valid key for an "
            "identity nobody owns."
        )

    return " ".join(words)


def to_seed(phrase: str, passphrase: str = "") -> bytes:
    """Turns a recovery phrase into its 64-byte BIP-39 seed.

    :raises ValueError: if the phrase is not a valid mnemonic
    """
    return hashlib.pbkdf2_hmac(
        "sha512",
        validate(phrase).encode("utf-8"),
        # BIP-39's salt: the passphrase is appended to the literal "mnemonic",
        # not passed separately.
        ("mnemonic" + _nfkd(passphrase)).encode("utf-8"),
        _ITERATIONS,
        _BIP39_SEED_SIZE,
    )


def _hkdf_sha512(ikm: bytes, info: bytes, length: int) -> bytes:
    """HKDF-SHA512 with an empty salt.

    An empty salt means a block of zero bytes of the hash length, which is
    what RFC 5869 specifies. Written out rather than taking a dependency:
    ``hashlib`` has PBKDF2 but no HKDF, and this is a dozen lines of HMAC
    checked against two other implementations.
    """
    digest_size = hashlib.sha512().digest_size
    prk = hmac.new(bytes(digest_size), ikm, hashlib.sha512).digest()

    okm, block, counter = b"", b"", 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha512).digest()
        okm += block
        counter += 1

    return okm[:length]


def derive_seed(key_type: KeyType, bip39_seed: bytes) -> bytes:
    """Turns a BIP-39 seed into the seed the given key type takes.

    :raises ValueError: if the seed is the wrong length, or the type has no
        seed derivation
    """
    if len(bip39_seed) != _BIP39_SEED_SIZE:
        raise ValueError(f"a BIP-39 seed is {_BIP39_SEED_SIZE} bytes, got {len(bip39_seed)}")

    if key_type is KeyType.SECP256K1:
        return hmac.new(b"Bitcoin seed", bip39_seed, hashlib.sha512).digest()[:32]

    if key_type in (KeyType.ML_DSA_65, KeyType.FALCON_512):
        info = f"activeledger-seed-v1:{key_type}".encode("utf-8")
        return _hkdf_sha512(bip39_seed, info, SEED_SIZES[key_type])

    raise ValueError(f"{key_type} keys cannot be derived from a seed")
