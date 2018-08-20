from activeLedgerSDK.primitives.user import identity
from activeLedgerSDK.primitives.transaction import baseTransaction
import requests
import json

def check_okay(identity_object):
    if identity_object.streamID and identity_object.key_object :
        return True
    else:
        return False

def createTransaction():
    return baseTransaction()

def sendTransaction(transaction_object, identity_object):
    transaction_message = transaction_object.transaction
    message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    try:
        r = requests.post(identity_object.address, data = json.dumps(transaction_message), headers = message_header, timeout = 10)
    except:
        raise Exception('Http post timeout')
    return json.loads(r.content.decode())




