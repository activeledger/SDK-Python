import json
import requests
from activeledgerPythonSDK.classes import key
from activeledgerPythonSDK.classes import Connection
from activeledgerPythonSDK.classes import resp


class baseTransaction(object):
    transaction = {
            
                '$territoriality':None,
                '$tx': {
                    '$namespace': None,
                    '$contract': None,
                    '$entry': None,
                    '$i': None,
                    '$o': None,
                    '$r': None,
                },
                '$selfsign': None,
                '$sigs': None,
            }
    def __init__(self):
        '''
        initialled as basic transaction
        '''
        self.jsonTransaction=json.dumps(self.transaction)
    
    def set_namespace(self, namespace):
            self.transaction['$tx']['$namespace'] = namespace
    
    def set_contract(self, contract):
 
        # if contract is not str:
        #     raise Exception('contract must be a string')
        # else:
        self.transaction['$tx']["$contract"]= contract
    
    def set_entry(self, entry):
        
        if type(entry) is not str:
            raise Exception('entry must be a string')
        else:
            self.transaction.get('$tx')['$entry'] = entry
    
    def set_i(self, i):
        if type(i) is not dict:
            raise Exception('i must be a dictionary')
        else:
            self.transaction.get('$tx')['$i'] = i
    
    def set_o(self, o):
        if type(o) is not dict:
            raise Exception('o must be a dictionary')
        else:
            self.transaction.get('$tx')['$o'] = o

    def set_r(self, r):
        if type(r) is not dict:
            raise Exception('r must be a dictionary')
        else:
            self.transaction.get('$tx')['$r'] = r
    
    def import_transaction(self, transaction_object):
        '''
        import transaction object directly, user should build 
        the object according to activeldger documentation 
        '''
        if transaction_object is not dict:
            raise Exception('transaction object must be a dictionary')
        else:
            self.transaction = transaction_object
    def createTransaction(self, selfsign,trtlty,streamID,keyPair,keyName,keyType):
   
    
        input=self.transaction.get('$tx')['$i']
        
        for inp in input.values(): 
         inp["$stream"]=streamID
         temp={keyName:inp}
        self.transaction.get('$tx')['$i']=temp

        txObj = json.loads(json.dumps(self.transaction.get('$tx')), object_hook=remove_nulls)
        sig=keyPair.create_signature(txObj)
        
        self.transaction["$selfsign"]=selfsign
        self.transaction["$sigs"]={streamID:sig}
        res = json.loads(json.dumps(self.transaction), object_hook=remove_nulls)
       
        return res

    def sendTransaction(self,tx,conn):
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        try:
            r = requests.post(conn.getConnectionURL(), data = json.dumps(tx), headers = message_header, timeout = 10)
        except:
            raise Exception('Http post timeout')

        alResponse = json.loads(r.content.decode())
        response =resp.Resp()
        if alResponse.get('$streams') is not None and alResponse.get('$streams').get('new')[0].get('id') is not None:
            response.setCode("200")
            response.setDesc(alResponse.get('$streams').get('new')[0].get('id'))
        elif alResponse.get('$streams') is not None and alResponse.get('$streams').get('updated')[0].get('id') is not None:
            response.setCode("200")
            response.setDesc(alResponse.get('$streams').get('updated')[0].get('id'))
        else:
            response.setCode("400")
            response.setDesc(alResponse.get('$summary').get('errors')[0])

        return response

    def createAndSendTrnsaction(self,conn,selfsign,trtlty,streamID,keyPair,keyName,keyType):
        
        tx=self.createTransaction(selfsign,trtlty,streamID,keyPair,keyName,keyType)
        return self.sendTransaction(tx,conn)



def remove_nulls(d):
    return {k: v for k, v in d.items() if v is not None}