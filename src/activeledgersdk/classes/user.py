from activeledgersdk.classes import key
from activeledgersdk.classes import transaction 
import json
import requests

class User(object):
    '''
    user object class for activeledger functions;
    including onboarding and send transactions.
    '''

    def __init__(self):
        '''
        initialization of user object
        '''
        self.key = None

    def add_key(self, key_class):
        '''
        add key object to this user class
        key_class expect key object type
        '''
        if self.key is None and type(key_class) is key.Key:
            self.key = key_class
        else:
            if self.key is not None:
                print('{0} key already exist'.format(self.key.key_type))
            return None
    
    def remove_key(self):
        '''
        remove key if exist
        '''
        if self.key:
            self.key = None
        else:
            print('key is empty')
    
    def onboard_key(self, identity, address):
        '''
        onboard key to get stream id,
        identity help to identify the user for this onboarding and expect a string
        address is the http address and expect a string
        return None if fail and id as a string is succeed
        '''
        if type(address) is not str or type(identity) is not str:
            raise Exception('address and identity must be string')
        
        if self.key is None:
            print('key is empty')
            return None
        else:
            message = {
                '$namespace': 'default',
                '$contract': 'onboard',
                '$i': {
                    identity: {
                        'publicKey': self.key.key_object.get('pub').get('pkcs8pem'),
                        'type': self.key.key_type
                    }
                }
            }
            sig_string = self.key.create_signature(message)
            onboard_message = {
                "$tx": message,
                "$selfsign": True,
                "$sigs": {
                    identity: sig_string
                }
            }
            message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            try:
                r = requests.post(address, data = json.dumps(onboard_message), headers = message_header, timeout = 10)
            except:
                raise Exception('Http post timeout')
            res =json.loads(r.content.decode())
            id = res.get('$streams').get('new')[0].get('id')
        if id:
            print('onboarding succeed')
            return id
        else:
            print('onboarding fail')
            return None

    def issue_transaction(self, transaction_object):
        '''
        issue transaction for activeledger
        '''
        if transaction_object is not transaction.baseTransaction:
            raise TypeError('transaction object invalid')
        
        transaction_message = transaction_object.transaction
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.post(identity_object.address, data = json.dumps(transaction_message), headers = message_header, timeout = 10)
        except:
            raise Exception('Http post timeout')
        return json.loads(r.content.decode())
        


    



