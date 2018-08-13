from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
# from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import hashlib
import json
import base64


def generate(keytype, keysize = 2048):
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
    
    
    private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
    public_key = private_key.public_key()


    # ECCkey.public_key().export_key()

    key_object = {
      'pub': {
        'pkcs8pem': public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
        'hash': hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()
      },
      'prv': {
        'pkcs8pem': private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
        'hash': hashlib.sha256(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).hexdigest()
      }
    }
    return key_object