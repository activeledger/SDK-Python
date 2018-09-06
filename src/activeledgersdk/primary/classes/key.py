from activeLedgerSDK.primitives import keypairs

class Key(object):
    '''
    Key object class for activeLedger-sdk
    '''

    def __init__(self, keytype):
        if keytype == 'rsa':
            self.keytype = 'rsa'
        if keytype == 'secp256k1':
            self.keytype = 'secp256k1'
        raise ValueError('keytype not supported')
    
    # def generate_key(self):
    #     if 


Key('sss')