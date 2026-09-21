<img src="https://www.activeledger.io/wp-content/uploads/2018/09/Asset-23.png" alt="Activeledger" width="500"/>

# Activeledger SDK for Python

Python SDK for [Activeledger](https://github.com/activeledger/activeledger), with post-quantum identity support.

**Requires Activeledger 4.7.0+** for `ml-dsa-65` and `falcon-512`. Python 3.9+.

> **Rewritten.** The import root is now `activeledger`, not `activeledgerPythonSDK`, and the API changed throughout. The previous version dated from 2019, had no tests, and declared no dependencies while importing two.

---

## Install

> [!WARNING]
> **`pip install activeledger-sdk` does not work** — this package is not on
> PyPI yet. Install the wheel from the GitHub release:

```bash
pip install https://github.com/activeledger/SDK-Python/releases/download/v1.3.0/activeledger_sdk-1.3.0-py3-none-any.whl
```

Optional extras are installed alongside it:

```bash
pip install 'ecdsa>=0.19'          # secp256k1 (the [ec] extra)
pip install 'liboqs-python>=0.16'  # post-quantum (the [pq] extra)
```

The core has no dependencies. Post-quantum is opt-in because `liboqs-python`
builds liboqs from source on first import, needing git, CMake, a C compiler
and OpenSSL headers — mandatory for a client SDK would be close to unusable.

Verified: the wheel installs into a clean venv and derives keys, with the
BIP-39 wordlist included.


## Quick start

```python
from activeledger import Activeledger, KeyPair, KeyType

ledger = Activeledger("http://localhost:5260")

key = KeyPair.generate(KeyType.ML_DSA_65)
identity = ledger.onboard(key)
print(identity.stream_id)
```

---

## Key types

| Key type | Wire string | Public | Private | Signature | Encoding | Extra |
|---|---|---|---|---|---|---|
| ML-DSA-65 | `ml-dsa-65` | 1952 | 4032 | 3309 | base64 | `[pq]` |
| Falcon-512 | `falcon-512` | 897 | 1281 | 649-662, variable | base64 | `[pq]` |
| secp256k1 | `secp256k1` | 33 or 65 | 32 | ~70-72, variable | `0x` hex | `[ec]` |

Use **secp256k1** unless the identity must outlive a cryptographically
relevant quantum computer: roughly **22x smaller** per transaction, and every
byte is stored on the ledger permanently and replicated to every node. It also
works with hardware wallets and HSMs, and is the only way to sign for an
identity created before post-quantum support.

```bash
pip install activeledger-sdk[ec]
```

It installs `python-ecdsa`, which is pure Python with no build step — unlike
`coincurve` (libsecp256k1), which needs a C toolchain **and** rejects the
high-S signatures the ledger produces freely.

```python
from activeledger import Secp256k1KeyPair

key = Secp256k1KeyPair.generate()                    # compressed
full = Secp256k1KeyPair.generate(compressed=False)   # uncompressed

key.public_key       # "0x02a1b2..." - give this to the ledger
key.private_key      # store this

restored = Secp256k1KeyPair.from_keys(key.public_key, key.private_key)
verifier = Secp256k1KeyPair.from_public_key(key.public_key)
```

### secp256k1 is encoded nothing like the post-quantum keys

- **Keys are `0x`-prefixed hex, not base64.** The prefix is required rather
  than tolerated, because hex without it can decode as base64 into
  plausible-looking bytes of the wrong length.
- **Public keys have two valid lengths**, 33 compressed and 65 uncompressed,
  and the ledger accepts both. A length and a SEC1 point prefix that disagree
  are rejected by name.
- **Private scalars are always 32 bytes**, left-padded.
- **Signatures are SHA-256 → ECDSA → DER**, and DER length varies.

### low-S, in both directions

**Signing** is RFC 6979 deterministic and low-S. `python-ecdsa` does **not**
normalise on its own, and it matters: without the normalisation this SDK
applies, 4 of the 12 published vectors come out high-S and differ from the
canonical form. Low-S is not for the ledger, which accepts either, but for
`@noble/curves` — the reference for the JavaScript side — and for libsecp256k1
and Rust's `k256`, all of which reject high-S by default.

**Verification accepts high-S**, because the ledger verifies through OpenSSL
and produces high-S freely. Rejecting those would fail on roughly half of all
valid signatures, and the half that succeeded would look like an intermittent
fault. `python-ecdsa` is permissive here — measured against the vectors, it
accepts all 7 high-S cases — which is why it is used.

Because signing is deterministic, this SDK's signatures are byte-identical to
`@noble/curves` for the same key and message, asserted against published
reference bytes on every test run.

`KeyType.from_wire` parses `bitcoin` and `ethereum` as secp256k1, because the
ledger routes them to identical verification. They are never emitted.

## Post-quantum keys

| Type | Wire string | Public | Private | Signature |
| --- | --- | --- | --- | --- |
| ML-DSA-65 | `ml-dsa-65` | 1952 B | 4032 B | 3309 B, fixed |
| Falcon-512 | `falcon-512` | 897 B | 1281 B | **649-662 B, variable** |
| secp256k1 | `secp256k1` | 65 B | 32 B | ~70-72 B DER |
| RSA | `rsa` | - | - | - |

Post-quantum keys are base64 of raw algorithm bytes.

```python
key = KeyPair.generate(KeyType.FALCON_512)

key.public_key_b64      # give this to the ledger
key.private_key_b64     # keep this
key.key_type            # KeyType.FALCON_512

signature = key.sign(b"some bytes")
key.verify(b"some bytes", signature)     # True

# Reload later
same = KeyPair.from_keys(KeyType.FALCON_512, pub_b64, prv_b64)

# Verify-only, no private key
checker = KeyPair.from_public(KeyType.FALCON_512, pub_b64)
```

**Falcon signature length varies** -- never assume it fixed. **Signing is hedged** for both schemes: two signatures over the same message differ, and both verify. That matches the reference implementation; FIPS 204 permits a deterministic variant which is deliberately not used.

`verify()` returns `False` for a malformed signature rather than raising -- a caller should not have to tell "invalid" from "wrong shape".

---

## Seeds and recovery phrases

```python
from activeledger import Secp256k1KeyPair, recovery

key = Secp256k1KeyPair.from_seed(seed)                 # 32 bytes
key = Secp256k1KeyPair.from_phrase(phrase)             # BIP-39
key = Secp256k1KeyPair.from_phrase(phrase, "passphrase")
```

The same seed gives the same identity in every Activeledger SDK, which is what
makes a seed the portable private-key format — it is how a private key moves
between languages.

A seed of the wrong length is **refused, not padded**: a padded seed is a
different identity, not a malformed one. And for `secp256k1` the seed **is**
the private scalar, so it has to be a valid one — a seed of zero, or one at or
above the curve order, is refused rather than reduced mod *n*, because
reducing produces a perfectly functional key belonging to a different identity
and nothing downstream ever reports a problem.

The phrase is validated, wordlist **and** checksum. A mistyped phrase that is
not checked does not fail; it derives a valid key for an identity nobody owns,
and the only symptom is the ledger not recognising it.

`Secp256k1KeyPair.from_legacy_phrase()` recovers a phrase made by the older
`@activeledger/sdk-bip39` package — recovery only, never for new keys.

### Post-quantum keys cannot be derived from a seed here

**Every other Activeledger SDK can do this; this one cannot, and it is not an
oversight.** liboqs — the post-quantum backend — exposes no derandomised
signature keygen: `OQS_SIG_keypair` takes no seed and there is no
`OQS_SIG_keypair_derand`. `_keypair_derand` exists for KEMs only, verified in
the 0.14.0 headers and against liboqs `main`, so there is nothing for the
Python binding to wrap.

`KeyPair.from_seed()` raises `NotImplementedError` with that explanation
rather than being absent, so code ported from another SDK finds out here
instead of from a signature the ledger rejects.

Post-quantum identities still work fully — `generate()`, sign, verify, and
export as key bytes. Only seed derivation is unavailable, and lifting it means
moving off liboqs.

The derivation every SDK shares, for reference:

| Type | Seed from the BIP-39 seed `S` |
| --- | --- |
| `secp256k1` | `HMAC-SHA512("Bitcoin seed", S)[0..32]` |
| `ml-dsa-65` | `HKDF-SHA512(S, salt="", info="activeledger-seed-v1:ml-dsa-65", 32)` |
| `falcon-512` | `HKDF-SHA512(S, salt="", info="activeledger-seed-v1:falcon-512", 48)` |

`recovery.derive_seed()` implements all three, so the post-quantum seeds can
be derived here and used in an SDK that can consume them.

## Transactions

```python
from activeledger import TransactionBuilder

tx = (
    TransactionBuilder()
    .namespace("mynamespace")
    .contract("mycontract")
    .input(identity.stream_id, identity.signer, {"message": "hello"})
    .output(target_stream, {"amount": 10})
    .build()
)

response = ledger.submit(tx)
if not response.committed:
    raise RuntimeError(response.errors)

print(response.new_streams)   # stream ids created
print(response.responses)     # returnToRemote values
```

`.entry("update")` sets `$entry` for contracts with multiple entry points.

---

## Reading state

There is no separate read API and no storage URL. A node's storage service listens only on the node's own host, so a client cannot reach it.

State is read **through a transaction**: name streams in `$r`, and the contract hands values back with `returnToRemote`.

```python
tx = (
    TransactionBuilder()
    .namespace("mynamespace")
    .contract("mycontract")
    .input(identity.stream_id, identity.signer)
    .readonly("target", some_stream_id)     # becomes $r
    .build()
)

for value in ledger.submit(tx).responses:
    print(value)
```

---

## Events (SSE)

Subscription is a generator, so leaving the loop closes the connection:

```python
for event in ledger.events.subscribe():
    print(event.name, event.id, event.data)
    if finished:
        break        # connection closes here
```

Each event is a `LedgerEvent(name, data, id)`. `name` and `id` are `None` when the server did not send them.

The parser handles the framing rules that actually matter:

- multiple `data:` lines in one event concatenate with newlines -- treating them as separate events is the classic SSE bug
- `:` comment lines (heartbeats) are ignored, not delivered as empty events
- `event:` and `id:` never leak into the following event
- an event still pending when the stream ends is delivered

Subscribe to another path with `ledger.events.subscribe("/events/mystream")`.

There is no read timeout by default: event streams are long-lived, and a timeout would close them for being quiet.

---

## Signing elsewhere

Anything with `key_type`, `public_key_b64` and `sign(bytes)` satisfies the `Signer` protocol, so the core needs no crypto dependency:

```python
from activeledger import KeyType, TransactionBuilder

class HsmSigner:
    key_type = KeyType.ML_DSA_65

    @property
    def public_key_b64(self):
        return my_hsm.public_key()

    def sign(self, message: bytes) -> bytes:
        return my_hsm.sign(message)

tx = TransactionBuilder().namespace("n").contract("c").input(stream, HsmSigner()).build()
```

---

## Things that will bite you

**Always send the key type.** The ledger defaults a missing `type` to `"rsa"` and then attempts RSA verification against a base64 post-quantum blob. This SDK always sends it; if you hand-build an envelope, do the same.

**A rejected transaction is HTTP 200.** Check `response.committed`, never the status code.

**Errors are unhelpful by design.** A wrong type string, a wrong-length key, or signed bytes differing by one escape all come back as **1220 "Signature Incorrect"** -- never "unknown algorithm" or "bad key length". This SDK validates key lengths and type strings up front so these fail locally with a message naming the problem.

**Signatures cover `$tx` only**, not the envelope. `tx.signed_bytes()` shows exactly what was signed, which is the fastest way to diagnose a 1220.

---

## Canonical JSON

Signatures cover the exact bytes of `JSON.stringify($tx)` encoded UTF-8 -- no hash prefix, no length prefix, no key sorting. Python's `json.dumps` is wrong here by default in three ways, **all of which produce correct output on an ASCII-only integer payload**:

| Default | Problem |
| --- | --- |
| `ensure_ascii=True` | escapes non-ASCII to `\uXXXX` |
| `separators=(', ', ': ')` | inserts spaces |
| whole floats | prints `1.0`; JavaScript prints `1` |

`activeledger.canonical_json` handles all three, and is checked byte-for-byte against cross-language vectors generated by the JavaScript SDK.

```python
from activeledger import canonical_json
canonical_json({"whole": 1.0, "note": "café"})
```

---

## Testing

```bash
pip install -e '.[pq,dev]'
pytest
```

Integration tests need a live network. From an `activeledger` checkout:

```bash
npm run test:network:serve
```

then, with the URLs it prints:

```bash
AL_NODES=http://127.0.0.1:5510 AL_STORAGE=http://127.0.0.1:5509 pytest tests/integration
```

They skip when `AL_NODES` is unset.

Correctness is established against published cross-language vectors and a real 4-node network -- onboarding both post-quantum schemes, submitting transactions, and confirming a tampered payload is rejected -- not against a reading of the reference implementation.

---

## Licence

MIT
