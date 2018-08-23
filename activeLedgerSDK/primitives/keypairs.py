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

def generate(keytype, keysize = 2048):
  '''
  Generate the same fromat of key object as it is in activeledger
  '''

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

    # add support for python 2.7 unicode 
    if type(key_object.get('pub').get('pkcs8pem')) or type(key_object.get('prv').get('pkcs8pem')) is unicode:
      
      key_object = {
        'pub': {
          'pkcs8pem': public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
          'hash': hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()
        },
        'prv': {
          'pkcs8pem': private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
          'hash': hashlib.sha256(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).hexdigest()
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

    # add support for python 2.7 unicode 
    if type(key_object.get('pub').get('pkcs8pem')) or type(key_object.get('prv').get('pkcs8pem')) is unicode:
      
      key_object = {
        'pub': {
          'pkcs8pem': public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
          'hash': hashlib.sha256(public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)).hexdigest()
        },
        'prv': {
          'pkcs8pem': private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
          'hash': hashlib.sha256(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).hexdigest()
        }
      }

    return key_object
  else:
    raise Exception('keytype unrecognized')

def verify(keytype, pub_key, prv_key):
  '''
  Verification function to check if the public and private key pair is valid
  pub_key and prv_key are string format
  must be in the format of key_object
  '''
  if type(pub_key) is str and type(prv_key) is str:
    message = b'key value verification'
    try:
      private_key = serialization.load_pem_private_key(prv_key.encode(), None, default_backend())
      public_key = serialization.load_pem_public_key(pub_key.encode(), default_backend())
    except:
      raise Exception('key pairs format invalid')
  else:
    raise TypeError('input key pairs should be in string format')
        
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
  else:
    raise Exception('keytype not supported or not identified')
        

def sign(keytype, prv_key, message):
  '''
  sign function return a string from a message signed by private key
  the message should be in dic format
  private key is in string format
  '''
  if type(message) is not dict:
    raise Exception('message type error')
  elif type(prv_key) is not str:
    raise Exception('private key format invalid')
  else:
    try:
      private_key = serialization.load_pem_private_key(prv_key.encode(), None, default_backend())
    except:
      raise Exception('private key not recognized')
    message = json.dumps(message, separators=(',', ':')).encode()
    if keytype == 'rsa':
        signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    elif keytype == 'secp256k1':
        signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    else:
        raise Exception('key type error')
    try:
      sig_string = base64.b64encode(signature).decode()
      return sig_string
    except:
      raise Exception('signature failed to generate')


def export(key_object):
  '''
  Export function to export 
  '''
  if (key_object):   
    return key_object

