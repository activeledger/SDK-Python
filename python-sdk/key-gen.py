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



# a = generate('rsa', 2048)
# print(json.dumps(a, indent=2))

b = generate('secp256k1')
print(json.dumps(b, indent=2))

# sign_object = ECC.import_key(b.get('prv').get('pkcs8pem').encode())
# print(sign_object)
# sig_object = DSS.new(sign_object, 'fips-186-3')
# sig_object = PKCS1_v1_5.new(sign_object)
# print(sig_object.can_sign())

message = {
"$namespace": "default",
  "$contract": "onboard",
  "$i": {
    "identity": {
      "publicKey": b.get('pub').get('pkcs8pem'),
      "type": "secp256k1"
    }
  }
}

message = json.dumps(message).encode()


private_key = serialization.load_pem_private_key(b.get('prv').get('pkcs8pem').encode(), None, default_backend())
signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))

sig_string = base64.b64encode(signature).decode()

print(sig_string)
# message = 'apple'.encode()
# digest = SHA256.new()
# digest.update(message)


# sig = sig_object.sign(digest)
# sig_string = base64.b64encode(sig).decode()
# print(sig_string)

# sign_object2 = ECC.import_key(b.get('pub').get('pkcs8pem').encode())
# verifer = DSS.new(sign_object2, 'fips-186-3')
# verified = verifer.verify(digest, sig)

# print(sig)
# print('ddddddd')
# print(verified)
# print(sign_object)
# print(sign_object2)

onboard_message = {
  "$tx": {
    "$namespace": "default",
    "$contract": "onboard",
    "$i": {
      "identity": {
        "publicKey": b.get('pub').get('pkcs8pem'),
        "type": "secp256k1"
      }
    }
  },
  "$selfsign": True,
  "$sigs": {
    "identity": sig_string
  }
}
# MEYCIQCHa1dgR48qGRzluVycxFrBv26rgn7EgB+JxKbfiiw3IAIhAMjZk62sIP5\nMt0fIdHx46zzJ3VWdyCuVJtbVnScz6ngX
# print(json.dumps(onboard_message, indent=2))



import requests


# print(type(json.loads(json.dumps(onboard_message))))

url = 'http://testnet-uk.activeledger.io:5260'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
r = requests.post(url, data = json.dumps(onboard_message), headers = headers)



print(r)
print(r._content)

# ECCkey = ECC.generate(curve = 'secp256r1')
# b = ECCkey.public_key().export_key(format = 'PEM', compress = False)
# c = b = ECCkey.export_key(format = 'PEM', use_pkcs8 = True, compress = False, passphrase = None)

# d = hashlib.sha256(b.encode()).hexdigest()

# print(b)
# print(c)

# print(d)
