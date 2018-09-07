import sys 
sys.path.append('/home/jialin/Documents/python-sdk/src/')

from activeledgersdk.classes import key
import unittest
import requests
import json



class OnboardingKeyTypes(unittest.TestCase):
    key_types = ('rsa', 'secp256k1')

    def test_for_oboarding(self):
        '''
        test case for onboarding for different key types    
        '''
        for ktype in (self.key_types):
            key_object = key.Key(ktype)
            key_object.generate_key()

            message = {
            '$namespace': 'default',
            '$contract': 'onboard',
            '$i': {
                'test': {
                    'publicKey': key_object.key_object.get('pub').get('pkcs8pem'),
                    'type': ktype
                    }
                }
            }
            sig_string = key_object.create_signature(message)
            onboard_message = {
                "$tx": message,
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