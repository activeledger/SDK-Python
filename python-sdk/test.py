from Crypto.PublicKey import RSA
# from Crypto.Signature import PKCS1_PSS
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import base64

import json
import requests
import os


# generate a rsa key object
rsa_object = RSA.generate(2048)
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
f2.write(rsa_object.exportKey(
  format= 'PEM',
  passphrase = None,
  pkcs = 8 
))
f1.close
f2.close

priv_pkcs_8 = rsa_object.exportKey(format= 'PEM', passphrase = None, pkcs = 8 )

# f3 = open('private.pem', 'r')
sign_object = RSA.importKey(priv_pkcs_8)
# f3.close

# pub_key = base64.b64encode(rsa_object.publickey().exportKey()).decode()
# pub_key2 = rsa_object.publickey().exportKey().decode()

# print('____________________________')
# print(pub_key)
# print('____________________________')
# print(pub_key2)
# print('____________________________')


# binPrivKey = rsa_object.exportKey('DER')
# private_key = RSA.importKey(binPrivKey)


# create signature object with private key
sig_object = PKCS1_v1_5.new(sign_object)

print(sig_object.can_sign())

# create a hash object based on SHA256
hash_object = SHA256.new()

message = {
        "$namespace" : "default",
        "$contract" : "onboard",
        "$i" : {
        "identity" : {
          "publicKey" : rsa_object.publickey().exportKey().decode(),
          "type" : "rsa"
        }
      }
   }

print(type(json.dumps(message, indent=2)))

# message = base64.b64encode(json.dumps(message).encode())

message = base64.b64encode(json.dumps(message).encode())

# print(a)
# print('[[[[[[[[[[[[[')
# print(type(a))


# message = json.dumps(message, indent=2).encode()
# message = base64.b64encode(json.dumps(message, indent=2)).encode()



digest = SHA256.new()
digest.update(message)

# print(sig_object.can_sign())

sig = sig_object.sign(digest)


sig_string = base64.b64encode(sig).decode()


# print(sig_string)
# print((sig_string))


onboard_message = {
  '$tx' : {
    '$namespace' : 'default',
    '$contract' : 'onboard',
    '$i' : {
      'identity' : {
        'publicKey' : rsa_object.publickey().exportKey().decode(),
        'type' : 'rsa'
      }
    }
  },
  '$selfsign' : True,
  '$sigs' : {
    'identity' : sig_string,
  }
}


# f3 = open('message.json', 'w')
# f3.write(json.dumps(onboard_message, indent=2))
# f3.close



# print(type(json.loads((json.dumps(onboard_message)))))


# print(type(onboard_message))
headers = {'Content-type': 'application/json; charset=utf8'}
r = requests.post('http://testnet-usa.activeledger.io:5260', data= json.dumps(onboard_message), headers = headers)
print("----------")

# print(json.dumps(onboard_message))
# print("----------")
# print(json.dumps(onboard_message).encode())
# print(json.dumps(onboard_message))

# print(type(json.dumps(onboard_message, indent= 2)))

# headers = {'Content-type': 'application/json; charset=utf8'}

# r = requests.post('http://35.195.221.172:5260', data= json.dumps(onboard_message), headers=headers)
print(r.status_code)
print(r._content)
# url = "http://localhost:8080"
# data = {'sender': 'Alice', 'receiver': 'Bob', 'message': 'We did it!'}
# r = requests.post(url, data=json.dumps(data), headers=headers)

# print(json.dumps(json.loads(str(r._content.decode('utf-8'))), indent= 2))
# print(r.status_code)

