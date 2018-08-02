
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import base64

import json
import requests

# generate a rsa key object
rsa_object = RSA.generate(1024)
# print(rsa_object.publickey().exportKey())
# print(rsa_object.exportKey())

# create signature object with private key
sig_object = PKCS1_v1_5.new(rsa_object)

# create a hash object based on SHA256
hash_object = SHA256.new()

# return a byte string signature
signature = sig_object.sign(hash_object)

# encoed the signature as a string
signature_str = base64.b64encode(signature)

# print(bytes.decode(signature))
# print(base64.b64encode(signature))
# PKCS1_v1_5.PKCS115_SigScheme.

# print(PKCS1_v1_5.PKCS115_SigScheme.sign(hash_object))

# now we need to update the information (need to be byte string format)

# strings = {'identity': str(signature_str)}
onboard_message = {
  "$tx" : {
    "$namespace" : "default",
    "$contract" : "onboard",
    "$i" : {
      "Jialin" : {
        "publicKey" : str(rsa_object.publickey().exportKey()),
        "type" : "secp256k1"
      }
    }
  },
  "$selfsign" : True,
  "$sigs" : {
    "identity" : str(signature_str)
  }
}
# print(str(signature_str))
# print(type(str(signature_str)))

# print(json.dumps(onboard_message))

r = requests.post('http://35.195.221.172:5260', json = [json.dumps(onboard_message)])
# r.content()
print(str(r._content))
print(r.status_code)


# }
# hash_object.update()

# print(hash_object)


# print(key1.publickey().exportKey())

# a = key.exportKey()



# print(PKCS1_v1_5.new(key1.exportKey()))

# h = SHA256.new()
# h.update(b'hhh')

# print(base64.b64decode(PKCS1_v1_5.new(key1.exportKey()).sign(h)))
# f = open('a.pem', 'wb')

# f.write(a)


# print(a)