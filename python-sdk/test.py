from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import base64

import json
import requests
import os

# generate a rsa key object
rsa_object = RSA.generate(1024)

# store the public and private key for this rsa object


def renew_key(filename):
    try:
        os.remove(filename)
    except:
        print(f'No file found, create file {filename}')


renew_key('public.pem')
renew_key('private.pem')


f1 = open('public.pem', 'wb')
f2 = open('private.pem', 'wb')
f1.write(rsa_object.publickey().exportKey())
f2.write(rsa_object.exportKey())
f1.close
f2.close




# print(rsa_object.publickey().exportKey())
# print(str(rsa_object.exportKey().decode('utf-8')))
# print(str(rsa_object.exportKey()).lstrip())
# print(str(rsa_object.exportKey().decode('utf-8')))

# create signature object with private key
sig_object = PKCS1_v1_5.new(rsa_object)

# create a hash object based on SHA256
hash_object = SHA256.new()

message_object = {
    "$namespace" : "default",
    "$contract" : "onboard",
    "$i" : {
      "identity" : {
        "publicKey" : str.encode(json.dumps()),
        "type" : "secp256k1"
      }
    }
} 

# print(type(json.dumps(message_object)))
print(json.dumps(message_object))
hash_object.update(str.encode(json.dumps(message_object)))

# print(type(str.encode('aaa')))
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
      "identity" : {
        "publicKey" : str(rsa_object.publickey().exportKey().decode('utf-8')),
        "type" : "rsa"
      }
    }
  },
  "$selfsign" : True,
  "$sigs" : {
    "identity" : str(signature_str.decode('utf-8'))
  }
}
# print(str(signature_str))
# print(type(str(signature_str)))

print(type(json.dumps(onboard_message)))

headers = {'Content-type': 'application/json'}
r = requests.post('http://35.195.221.172:5260', data = json.dumps(onboard_message), headers = headers)
# print(r.status_code)
# print(r._content)
# url = "http://localhost:8080"
# data = {'sender': 'Alice', 'receiver': 'Bob', 'message': 'We did it!'}
# r = requests.post(url, data=json.dumps(data), headers=headers)

print(r._content)
# print(r.status_code)


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