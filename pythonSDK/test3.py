from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import hashlib
import json
import base64
import binascii


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

f3 = open('key.json', 'w')
f3.write(json.dumps(a, indent=2))
f3.close




f1 = open('public.pem', 'w')
f2 = open('private.pem', 'w')
f1.write(a.get('pub').get('pkcs8pem'))
f2.write(a.get('prv').get('pkcs8pem'))
f1.close
f2.close

# sign_object = RSA.importKey(priv_pkcs_8)

sign_object = RSA.importKey(a.get('prv').get('pkcs8pem').encode())

sig_object = PKCS1_v1_5.new(sign_object)

message = {
  "$namespace": "default",
  "$contract": "onboard",
  "$i": {
    "identity": {
      "type": "rsa",
      "publicKey": a.get('pub').get('pkcs8pem')
    }
  }
}


message = json.dumps(message, separators=(',', ':')).encode()


# message = bytes(str("hello"), 'utf-8')

# message = bytes(str(message), 'utf-8')


# message = base64.standard_b64encode(json.dumps(message))
# message = bytes(json.dumps(message))
# message = base64.b64encode (bytes(json.dumps(message), "utf-8"))
# print("---------------------")
# print(message)
# print("---------------------")
# print(json.dumps(message))
# print("---------------------")
# message = base64.b64encode(json.dumps(message))
# print(message)
# print("---------------------")




digest = SHA256.new()
digest.update(message)

sig = sig_object.sign(digest)
sig_string = base64.b64encode(sig).decode()

# print(type(sig_string))
# print(sig_string)

onboard_message = {
  "$tx": {
    "$namespace": "default",
    "$contract": "onboard",
    "$i": {
      "identity": {
        "type": "rsa",
        "publicKey": a.get('pub').get('pkcs8pem')
      }
    }
  },
  "$selfsign": True,
  "$sigs": {
    "identity": sig_string,
  }
}

# f3 = open('transaction.json', 'w')
# f3.write(json.dumps(onboard_message, indent=2))
# f3.close


import requests

url = 'http://testnet-uk.activeledger.io:5260'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
r = requests.post(url, data = json.dumps(onboard_message), headers = headers)


print(r)
# print(r._content)
print(json.dumps(r._content.decode(), indent=2))


# a = json.dumps(generate('rsa', 2048), indent= 2)


