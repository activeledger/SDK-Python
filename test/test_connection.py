from activeLedgerSDK.primitives import keypairs
import unittest
import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import ec
import requests
import json
import base64
import ast


class OnboardingKeyTypes(unittest.TestCase):
    key_types = ('rsa', 'secp256k1')

    def test_for_oboarding(self):
        '''
        test case for onboarding for different key types    
        '''
        for ktype in (self.key_types):
            key_object = keypairs.generate(ktype)
            
            message = {
            '$namespace': 'default',
            '$contract': 'onboard',
            '$i': {
                'test': {
                    'publicKey': key_object.get('pub').get('pkcs8pem'),
                    'type': ktype
                    }
                }
            }

            message = json.dumps(message, separators=(',', ':')).encode()
            private_key = serialization.load_pem_private_key(key_object.get('prv').get('pkcs8pem').encode(), None, default_backend()) 

            if ktype == 'rsa':
                signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            elif ktype == 'secp256k1':
                signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            
            if type(message) is str:
                sig_string = base64.b64encode(signature)

                onboard_message = {
                    "$tx": ast.literal_eval(json.dumps(json.loads(message), separators=(',', ':'))),
                    "$selfsign": True,
                    "$sigs": {
                        'test': sig_string
                    }
                }
            else:
                sig_string = base64.b64encode(signature).decode()
                onboard_message = {
                    "$tx": json.loads(message.decode()),
                    "$selfsign": True,
                    "$sigs": {
                        'test': sig_string
                    }
                }

            message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}

            try:
                r = requests.post('http://testnet-uk.activeledger.io:5260', data = json.dumps(onboard_message), headers = message_header, timeout = 10)
            except:
                raise Exception('Http post timeout')

            respond = json.loads(r.content.decode())
            id = respond.get('$streams').get('new')[0].get('id')

            self.assertTrue(id)

if __name__ == '__main__':
    unittest.main()