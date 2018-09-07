from activeledgersdk.primitives import keypairs
import hashlib

class Key(object):
    '''
    Key object class for activeLedger-sdk
    '''
    key_object = None
    key_type = None

    def __init__(self, keytype):
        '''
        initialize key object with keytype
        error raise when keytype not identified and interupt object initialization
        '''
        if keytype == 'rsa':
            self.key_type = 'rsa'
        if keytype == 'secp256k1':
            self.key_type = 'secp256k1'
        if self.key_type == None:
            raise ValueError('keytype not supported')
    
    def generate_key(self, keysize = 2048):
        '''
        keysize only work for rsa key type and the minimum length for rsa key is 1024(default 2048);
        unless the user has knowledge about cryptography,please use just use **generate_key()**
        '''
        if self.key_object is None:
            self.key_object = keypairs.generate(self.key_type, keysize)
        else:
            print('{0} key type exist'.format(self.key_type))
    
    def import_key(self, publickey, privatekey):
        '''
        import key option for user who wish to use their own existing key,
        publickey and privatekey must be in pkcs8pem string format which 
        distinctive with "-----BEGIN {format}-----" and "-----END {format}-----"
        '''
        if self.key_object is not None:
            print('{0} key type exist'.format(self.key_type))
        else:
            key_object = {               
                'pub': {
                'pkcs8pem': publickey,
                'hash': hashlib.sha256(publickey.encode()).hexdigest()
                },
                'prv': {
                'pkcs8pem': privatekey,
                'hash': hashlib.sha256(privatekey.encode()).hexdigest()
                }
            }
            key_is_ok = keypairs.verify(self.key_type, key_object)
            if key_is_ok:
                self.key_object = key_object
            else:
                print('{0} key not valid'.format(self.key_type))
    
    def create_signature(self, message):
        '''
        create signature based on key type and message;
        message must be a dictionary and this function returns a string.
        '''
        if self.key_object is None:
            raise ValueError('{0} key not exist'.format(self.key_type))
        return keypairs.sign(self.key_type, self.key_object, message)
        

    
    