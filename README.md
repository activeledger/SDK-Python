<img src="https://www.activeledger.io/wp-content/uploads/2018/09/Asset-23.png" alt="Activeledger" width="500"/>

# Activeledger SDK for Python

Python SDK for [Activeledger](https://github.com/activeledger/activeledger), with post-quantum identity support.

**Requires Activeledger 4.7.0+** for `ml-dsa-65` and `falcon-512`. Python 3.9+.

> **Rewritten.** The import root is now `activeledger`, not `activeledgerPythonSDK`, and the API changed throughout. The previous version dated from 2019, had no tests, and declared no dependencies while importing two.

---

## Install

```bash
pip install activeledger-sdk           # core: zero dependencies
pip install 'activeledger-sdk[pq]'     # + post-quantum signing
```

**Why two.** Post-quantum signing uses `liboqs-python`, which does *not* bundle liboqs -- on first import it builds it from source, needing git, CMake, a C compiler **and** OpenSSL headers. Making that mandatory would break `pip install` for anyone without all four. So the core is stdlib-only and post-quantum is opt-in.

You only need `[pq]` if this SDK generates or uses keys. If you sign elsewhere -- an HSM, a signing service, a user's wallet -- the core alone builds, signs and submits transactions with no compiled dependency at all.

Ask for a post-quantum key without the extra and you get an `ImportError` naming it, not a CMake traceback from inside a dependency.

---

## Quick start

```python
from activeledger import Activeledger, KeyPair, KeyType

ledger = Activeledger("http://localhost:5260")

key = KeyPair.generate(KeyType.ML_DSA_65)
identity = ledger.onboard(key)
print(identity.stream_id)
```

---

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
