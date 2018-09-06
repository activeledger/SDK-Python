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


class SendTransactions(unittest.TestCase):
    key_types = ('rsa', 'secp256k1')

    def get_onboard_id(self, keytype):
        '''
        get two new identity for keytype
        '''
        key_object_1 = keypairs.generate(keytype)
        key_object_2 = keypairs.generate(keytype)

        message_1 = {
            '$namespace': 'default',
            '$contract': 'onboard',
            '$i': {
                'test': {
                    'publicKey': key_object_1.get('pub').get('pkcs8pem'),
                    'type': keytype
                }
            }
        }

        message_2 = {
            '$namespace': 'default',
            '$contract': 'onboard',
            '$i': {
                'test': {
                    'publicKey': key_object_2.get('pub').get('pkcs8pem'),
                    'type': keytype
                }
            }
        }

        message1 = json.dumps(message_1, separators=(',', ':')).encode()
        message2 = json.dumps(message_2, separators=(',', ':')).encode()

        private_key_1 = serialization.load_pem_private_key(key_object_1.get('prv').get('pkcs8pem').encode(), None, default_backend()) 
        private_key_2 = serialization.load_pem_private_key(key_object_2.get('prv').get('pkcs8pem').encode(), None, default_backend()) 

        if keytype == 'rsa':
            signature_1 = private_key_1.sign(message1, padding.PKCS1v15(), hashes.SHA256())
            signature_2 = private_key_2.sign(message2, padding.PKCS1v15(), hashes.SHA256())
        elif keytype == 'secp256k1':
            signature_1 = private_key_1.sign(message1, ec.ECDSA(hashes.SHA256()))
            signature_2 = private_key_2.sign(message2, ec.ECDSA(hashes.SHA256()))

        if type(message1) is str:
            sig_string1 = base64.b64encode(signature_1)
            sig_string2 = base64.b64encode(signature_2)

            onboard_message1 = {
                "$tx": ast.literal_eval(json.dumps(json.loads(message1), separators=(',', ':'))),
                "$selfsign": True,
                "$sigs": {
                    'test': sig_string1
                }
            }

            onboard_message2 = {
                "$tx": ast.literal_eval(json.dumps(json.loads(message2), separators=(',', ':'))),
                "$selfsign": True,
                "$sigs": {
                    'test': sig_string2
                }
            }
        else:
            sig_string1 = base64.b64encode(signature_1).decode()
            sig_string2 = base64.b64encode(signature_2).decode()

            onboard_message1 = {
                "$tx": json.loads(message1.decode()),
                "$selfsign": True,
                "$sigs": {
                    'test': sig_string1
                }
            }

            onboard_message2 = {
                "$tx": json.loads(message2.decode()),
                "$selfsign": True,
                "$sigs": {
                    'test': sig_string2
                }
            }
            
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        try:
            r1 = requests.post('http://testnet-uk.activeledger.io:5260', data = json.dumps(onboard_message1), headers = message_header, timeout = 10)
            r2 = requests.post('http://testnet-uk.activeledger.io:5260', data = json.dumps(onboard_message2), headers = message_header, timeout = 10)
        except:
            raise Exception('Http post timeout')

        respond1 = json.loads(r1.content.decode())
        respond2 = json.loads(r2.content.decode())
        id1 = respond1.get('$streams').get('new')[0].get('id')
        id2 = respond2.get('$streams').get('new')[0].get('id')

        return (id1, id2, key_object_1)

    def test_send_transaction(self):

        for keytypes in self.key_types:
            (id1, id2, key_object) = self.get_onboard_id(keytypes)

            message = {
                "$namespace": "ns2",
                "$contract": "df9f84846ace992d7aa13b8f7d4295b4a0d54f178e0059d96208dd1b2183b297",
                "$entry": "transfer",
                "$i": {
                    str(id1): {
                        "symbol" : "usd",
                        "amount" : 5
                    }
                },
                "$o": {
                    str(id2): {
                        "amount" : 5
                    }
                }
            }

            message = json.dumps(message, separators=(',', ':')).encode()
            private_key = serialization.load_pem_private_key(key_object.get('prv').get('pkcs8pem').encode(), None, default_backend()) 

            if keytypes == 'rsa':
                signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
            elif keytypes == 'secp256k1':
                signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            
            if type(message) is str:
                sig_string = base64.b64encode(signature)

                tran_message = {
                    "$tx": ast.literal_eval(json.dumps(json.loads(message), separators=(',', ':'))),
                    "$selfsign": False,
                    "$sigs": {
                        str(id1): sig_string
                    }
                }

                # print(json.dumps(tran_message, separators=(',', ':')))             
            else:
                sig_string = base64.b64encode(signature).decode()

                tran_message = {
                    "$tx": json.loads(message.decode()),
                    "$selfsign": False,
                    "$sigs": {
                        id1: sig_string
                    }
                }

                # print(json.dumps(tran_message, separators=(',', ':')))/
            
            
            message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}

            try:
                r = requests.post('http://testnet-uk.activeledger.io:5260', data = json.dumps(tran_message), headers = message_header, timeout = 10)
            except:
                raise Exception('Http post timeout')

            respond = json.loads(r.content.decode())
            total = respond.get('$summary').get('total')
            commit = respond.get('$summary').get('commit')
            print(respond)
            self.assertTrue(total == commit)


if __name__ == '__main__':
    unittest.main()