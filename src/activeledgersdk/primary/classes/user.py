from activeledgersdk.primary.classes import key
import os 
import json
import hashlib

class User(object):
    '''
    basic object class for identity management
    one identiy only allows to one type of keys 
    to use multiple keys please create multiple identity
    '''

    def __init__(self, identity):
        '''
        expected a string format
        if a non-string is given the default object identity is 'identity'
        create folder to create keypairs when initialize object
        if exit folder donot do anything
        '''
        if type(identity) is str:
            self.identity = identity
        else:
            self.identity = 'identity'
        if not os.path.exists('./sdk-keypairs/'):
            os.makedirs('./sdk-keypairs/')
        if not os.path.exists('./sdk-transactions/'):
            os.makedirs('./sdk-transactions/')
        if not os.path.exists('./sdk-identities/'):
            os.makedirs('./sdk-identities/')
        
    def generate_key(self, keytype, keysize = 2048):
        try:
            self.key_object = keypairs.generate(keytype, keysize)
            self.key_type = keytype       
        except:
            print('keytype not supported')
    
    def export_key(self):
        '''
        export_key function automatically create three files
        one JSON file and two PEM files
        '''
        try:
            keypairs.export(self.key_object)
            f1 = open('./sdk-keypairs/{}_public.pem'.format(self.identity), 'w')
            f2 = open('./sdk-keypairs/{}_private.pem'.format(self.identity), 'w')
            f3 = open('./sdk-keypairs/{}_key.json'.format(self.identity), 'w')
            f1.write(self.key_object.get('pub').get('pkcs8pem'))
            f2.write(self.key_object.get('prv').get('pkcs8pem'))
            f3.write(json.dumps(self.key_object, indent=2, separators=(',', ':')))
            f1, f2, f3.close
        except:
            print('Key information does not exist,please either generate a new or import your own key')
    
    def import_key(self, key_type, pub_key, prv_key):
        '''
        **NOTE: this is erase existing keypairs in the identity class**
        
        import_key function only accept files with pkcs8pem format
        the user should put their own keys in the 'sdk-keypairs' folder at their working directory
        pub_key, prv_key are file names for public key and private key in .pem format
        '''
        try:
            f1 = open('./sdk-keypairs/{}'.format(pub_key), 'r')
            f2 = open('./sdk-keypairs/{}'.format(prv_key), 'r')
            pub_key = f1.read()
            prv_key = f2.read()
            f1, f2.close
        except:
            raise Exception('key pair file(s) not exist')
        
        key_OK = keypairs.verify(key_type, pub_key, prv_key)
        if key_OK:
            key_object = {               
                'pub': {
                'pkcs8pem': pub_key,
                'hash': hashlib.sha256(pub_key.encode()).hexdigest()
                },
                'prv': {
                'pkcs8pem': prv_key,
                'hash': hashlib.sha256(prv_key.encode()).hexdigest()
                }
            }
            self.key_object = key_object
            self.key_type = key_type
        else:
            raise Exception('fail to import key pair')
    
    def setHTTP(self, address):
        '''
        setHTTP function set the post address for current identity
        it should in the from like: 'http://testnet-uk.activeledger.io:5260'
        '''
        if type(address) is not str:
            raise Exception('http post address must be a string')
        else:
            self.address = address

    def sign(self, message):
        '''
        sign function and return a signature in base64 string format
        message should be in dic format
        '''
        try:
            keypairs.sign(self.key_type, self.key_object.get('prv').get('pkcs8pem'), message)
        except:
            raise Exception('Information missing for signing')


    def setStreamID(self, respond):
        '''
        set stream id after onboarding
        respond is the respond from activeledger
        this will also create a json file containing the respond
        '''
        if type(respond) is not dict:
            raise Exception('format unrecognized, please use default respond')
        else:
            try:
                id = respond.get('$streams').get('new')[0].get('id')
                f = open('./sdk-identities/{}_onboard.json'.format(self.identity), 'w')
                f.write(json.dumps(respond, indent=2, separators=(',', ':')))
                f.close
            except:
                print('unrecognized information')
        self.streamID = id
    
    def importStreamID(self, filename):
        '''
        import stream id for existing
        **NOTE** this will erase any existing stream id
        '''
        try:
            f = open('./sdk-identities/{}'.format(filename), 'r')
            stream_content = f.read()
            f.close
        except:
            raise Exception('identity file not exist')
        try:
            res = json.loads(stream_content)
            self.setStreamID(res)
        except:
            raise Exception('identity content not recognized')

        


    



