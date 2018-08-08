from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import hashlib
import json
import base64


def generate(keytype, keysize):
  # return the same object formst as the activeledger
  if keytype == 'rsa':
    RSAkey = RSA.generate(keysize)

    key_object = {
      'pub': {
        'pkcs8pem': RSAkey.publickey().exportKey('PEM', None, pkcs = 8).decode(),
        'hash': hashlib.sha256(RSAkey.publickey().exportKey('PEM', None, pkcs = 8)).hexdigest()
      },
      'prv': {
        'pkcs8pem': RSAkey.exportKey('PEM', None, pkcs = 8).decode(),
        'hash': hashlib.sha256(RSAkey.exportKey('PEM', None, pkcs = 8)).hexdigest()
      }
    }
    return key_object
  if keytype == 'secp256k1':
    return key_object


a = generate('rsa', 2048)

# sign_object = RSA.importKey(priv_pkcs_8)

sign_object = RSA.importKey(a.get('prv').get('pkcs8pem').encode())

sig_object = PKCS1_v1_5.new(sign_object)

message = {
  "$namespace": "default",
  "$contract": "onboard",
  "$i": {
    "identity": {
      "publicKey": a.get('pub').get('pkcs8pem'),
      "type": "rsa"
    }
  }
}

message = json.dumps(message).encode()

digest = SHA256.new()
digest.update(message)

sig = sig_object.sign(digest)
sig_string = base64.b64encode(sig).decode()

# print(type(sig_string))

onboard_message = {
  "$tx": {
    "$namespace": "default",
    "$contract": "onboard",
    "$i": {
      "identity": {
        "publicKey": a.get('pub').get('pkcs8pem'),
        "type": "rsa"
      }
    }
  },
  "$selfsign": True,
  "$sigs": {
    "identity": sig_string,
  }
}

import requests

url = 'http://testnet-uk.activeledger.io:5260'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
r = requests.post(url, data = json.dumps(onboard_message), headers = headers)


print(r)
print(r._content)


# a = json.dumps(generate('rsa', 2048), indent= 2)

a = generate('rsa', 2048).get('pub').get('hash')

print(a)


