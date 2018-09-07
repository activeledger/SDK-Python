import sys 
sys.path.append('/home/jialin/Documents/python-sdk/src/')

from activeledgersdk.classes import user
from activeledgersdk.classes import key

from activeLedgerSDK.primitives import keypairs
import unittest
import json

import requests
import json



class SendTransactions(unittest.TestCase):
    key_types = ('rsa', 'secp256k1')

    def test_send_transaction(self):

        for keytypes in self.key_types:
            key_object = key.Key(keytypes)
            key_object.generate_key()
            user_object = user.User()
            user_object.add_key(key_object)
            id1 = user_object.onboard_key('test', 'http://testnet-uk.activeledger.io:5260')
            id2 = user_object.onboard_key('test', 'http://testnet-uk.activeledger.io:5260')

            message = {
                "$namespace": "ns2",
                "$contract": "df9f84846ace992d7aa13b8f7d4295b4a0d54f178e0059d96208dd1b2183b297",
                "$entry": "transfer",
                "$i": {
                    id1: {
                        "symbol" : "usd",
                        "amount" : 5
                    }
                },
                "$o": {
                    id2: {
                        "amount" : 5
                    }
                }
            }

            sig_string = key_object.create_signature(message)

            tran_message = {
                "$tx": message,
                "$selfsign": False,
                "$sigs": {
                    id1: sig_string
                }
            }
            
            message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}

            try:
                r = requests.post('http://testnet-uk.activeledger.io:5260', data = json.dumps(tran_message), headers = message_header, timeout = 10)
            except:
                raise Exception('Http post timeout')

            respond = json.loads(r.content.decode())
            total = respond.get('$summary').get('total')
            commit = respond.get('$summary').get('commit')
            self.assertTrue(total == commit)


if __name__ == '__main__':
    unittest.main()