from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
import base64

import json
import requests
import os
import urllib.request
    



# generate a rsa key object
rsa_object = RSA.generate(2048)

# store the public and private key for this rsa object

def renew_key(filename):
    try:
        os.remove(filename)
    except:
        print(f'No file found, create file {filename}')


def read_key(filename):
  f = open(filename, 'rb')
  t = f.read()
  return t

# renew_key('public.pem')
# renew_key('private.pem')


# f1 = open('public.pem', 'wb')
# f2 = open('private.pem', 'wb')
# f1.write(rsa_object.publickey().exportKey())
# f2.write(rsa_object.exportKey())
# f1.close
# f2.close


rsa_object = RSA.importKey(read_key('private.pem'))
# print(rsa_object)

# create signature object with private key
sig_object = PKCS1_v1_5.new(rsa_object)

# create a hash object based on SHA256
hash_object = SHA256.new()

message = 'hello'.encode()



# # message = json.dumps(message).encode()

digest = SHA256.new()
digest.update(message)

sig = sig_object.sign(digest)

sig_string = base64.b64encode(sig).decode()



print(sig_string)

verifier = PKCS1_v1_5.new(RSA.importKey(read_key('public.pem')))
verified = verifier.verify(digest, sig)

print(verified)

# print(type(sig_string))


# onboard_message = {
#   '$tx' : {
#     '$namespace' : 'default',
#     '$contract' : 'onboard',
#     '$i' : {
#       'identity' : {
#         'publicKey' : rsa_object.publickey().exportKey().decode(),
#         'type' : 'rsa'
#       }
#     }
#   },
#   '$selfsign' : True,
#   '$sigs' : {
#     'identity' : sig_string
#   }
# }



# body = onboard_message  

# myurl = "http://35.195.221.172:5260"
# req = urllib.request.Request(myurl)
# req.add_header('Content-Type', 'application/json; charset=utf-8')
# jsondata = json.dumps(body)
# jsondataasbytes = jsondata.encode('utf-8')   # needs to be bytes
# req.add_header('Content-Length', len(jsondataasbytes))
# print (jsondataasbytes)
# response = urllib.request.urlopen(req, jsondataasbytes)
# print(response.value)



# print(type(json.loads((json.dumps(onboard_message)))))


# print(type(onboard_message))
# headers = {'Content-type': 'application/json; charset=utf8'}
# r = requests.post('http://35.195.221.172:5260', data= json.dumps(onboard_message).encode(), headers = headers)
# print(r)

# print(type(json.dumps(onboard_message, indent= 2)))

# headers = {'Content-type': 'application/json; charset=utf8'}

# r = requests.post('http://35.195.221.172:5260', data= json.dumps(onboard_message), headers=headers)
# print(r.status_code)
# print(r._content)
# url = "http://localhost:8080"
# data = {'sender': 'Alice', 'receiver': 'Bob', 'message': 'We did it!'}
# r = requests.post(url, data=json.dumps(data), headers=headers)

# print(json.dumps(json.loads(str(r._content.decode('utf-8'))), indent= 2))
# print(r.status_code)

