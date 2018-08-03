import base64

from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA

message = 'apple'.encode()
digest = SHA256.new()
digest.update(message)

# print(type(message))
# print(message)

rsa_object = RSA.generate(2048)

sig_object = PKCS1_v1_5.new(rsa_object)
sig = sig_object.sign(digest)

verifier = PKCS1_v1_5.new(rsa_object.publickey())
verified = verifier.verify(digest, sig)

print(verified)

print(rsa_object.publickey().exportKey().decode())

print(type(rsa_object.publickey().exportKey().decode()))

