from ActiveLedgerSDK.primitives.user import identity

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

import requests
import json
import base64

def createIdentity(name):
    '''
    createIdentity(identity) create a identity object
    identity expects a string or 'identity' will be used by default
    identity is for SDK user to identity their own identity from client side
    the real identity will be generated automatically when onboading
    '''
    return identity(name)


def onboardIdentity(identity_object):
    '''
    onboard current identity object
    if success, return a python dictioinary 
    '''
    if type(identity_object) is not identity:
        raise Exception('input type invalid')
    if not identity_object.address:
        raise Exception('http address dont exist')
    if not identity_object.key_object:
        raise Exception('empty key pair')
    try:
        message = {
            "$namespace": "default",
            "$contract": "onboard",
            "$i": {
                identity_object.identity: {
                "publicKey": identity_object.key_object.get('pub').get('pkcs8pem'),
                "type": identity_object.key_type
                }
            }
        }

        message = json.dumps(message, separators=(',', ':')).encode()
        private_key = serialization.load_pem_private_key(identity_object.key_object.get('prv').get('pkcs8pem').encode(), None, default_backend())
    except:
        raise Exception('???')

    if identity_object.key_type == 'rsa':
        signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    elif identity_object.key_type == 'secp256k1':
        signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    else:
        raise Exception('key type error')
    try:
        sig_string = base64.b64encode(signature).decode()

        onboard_message = {
            "$tx": json.loads(message.decode()),
            "$selfsign": True,
            "$sigs": {
                identity_object.identity: sig_string
            }
        }
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.post(identity_object.address, data = json.dumps(onboard_message), headers = message_header, timeout = 10)
        except:
            raise Exception('Http post timeout')
        return json.loads(r.content.decode())
    except:
        print('Onboarding identity failed')
    

    
        


    
    



