from ActiveLedgerSDK.primitives.user import identity

def check_okay(identity_object):
    if identity_object.streamID and identity_object.key_object :
        return True
    else:
        return False

def createTransaction(identity_object)
