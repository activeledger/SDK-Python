from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

import hashlib
import json
import base64

'''
Updated on 5th Sep 2018
Use uniform parameter for function call
'''
def generate(keytype, keysize = 2048):
  '''
  Generate the same fromat of key object as it is in activeledger
  '''
  if keysize <= 1024:
    raise ValueError('key size must larger than 1024')

  if keytype == 'rsa':        
    private_key = rsa.generate_private_key(65537, keysize, default_backend())
    public_key = private_key.public_key()
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

  if keytype == 'secp256k1':
    private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
    public_key = private_key.public_key()
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
  
  raise ValueError('keytype unrecognized')

def verify(keytype, key_object):
  '''
  Verification function to check if the public and private key pair in the 
  key object is valid. In Python key_object is in dictionary format.
  '''
  if type(key_object) is dict:
    try:
      pub_key = key_object.get('pub').get('pkcs8pem')
      prv_key = key_object.get('prv').get('pkcs8pem')
      private_key = serialization.load_pem_private_key(prv_key.encode(), None, default_backend())
      public_key = serialization.load_pem_public_key(pub_key.encode(), default_backend())
      message = b'key value verification'
    except:
      raise ValueError('key information error')
  else:
    raise TypeError('key object should be in dictionary format')
 
  if keytype == 'rsa':
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    try:
      public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
      return True
    except:
      return False
  
  if keytype == 'secp256k1':
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    try:
      public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
      return True
    except:
      return False
  
  raise ValueError('keytype unrecognized')
  
        

def sign(keytype, key_object, message):
  '''
  sign function return a string from a message signed by private key
  the message should be in dic format
  private key is derived from key object which is in dic format
  '''
  if type(message) is dict and type(key_object) is dict:
    try:
      prv_key = key_object.get('prv').get('pkcs8pem')
      private_key = serialization.load_pem_private_key(prv_key.encode(), None, default_backend())
      message = json.dumps(message, separators=(',', ':')).encode()
    except:
      raise ValueError('key information error')

    if keytype == 'rsa':
      signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
      sig_string = base64.b64encode(signature).decode()
      return sig_string
    
    if keytype == 'secp256k1':
      signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
      sig_string = base64.b64encode(signature).decode()
      return sig_string
    
    raise ValueError('keytype unrecognized')
  
  raise TypeError('type dont recognize')


