import json



class baseTransaction(object):

    def __init__(self):
        '''
        initialled as basic transaction
        '''
        self.transaction = {
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
    
    def set_namespace(self, namespace):
        if namespace is not str:
            raise Exception('namespace must be a string')
        else:
            self.transaction.get('$tx')['$namespace'] = namespace
    
    def set_contract(self, contract):
        if contract is not str:
            raise Exception('contract must be a string')
        else:
            self.transaction.get('$tx')['$contract'] = contract
    
    def set_entry(self, entry):
        if entry is not str:
            raise Exception('entry must be a string')
        else:
            self.transaction.get('$tx')['$entry'] = entry
    
    def set_i(self, i):
        if i is not dict:
            raise Exception('i must be a dictionary')
        else:
            self.transaction.get('$tx')['$i'] = i
    
    def set_o(self, o):
        if o is not dict:
            raise Exception('o must be a dictionary')
        else:
            self.transaction.get('$tx')['$o'] = o

    def set_r(self, r):
        if r is not dict:
            raise Exception('r must be a dictionary')
        else:
            self.transaction.get('$tx')['$r'] = r
    
    def import_transaction(self, filename):
        '''
        import transaction from file 
        the default path is in sdk-contracts folder
        user need to provide a full transaction file
        '''
        try:
            f = open('./sdk-transactions/{}'.format(filename), 'r')
            transaction_object = f.read()
            f.close
        except:
            raise Exception('file don not exist')
        transaction_json = json.loads(transaction_object)
        if '$tx' and '$selfsign' and '$sigs' not in transaction_json:
            raise Exception('transaction not recognized')
        else:
            try:
                if '$namespace' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$namespace'] = transaction_json.get('$tx').get('$namespace')
                if '$contract' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$contract'] = transaction_json.get('$tx').get('$contract')
                if '$entry' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$entry'] = transaction_json.get('$tx').get('$entry')
                if '$i' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$i'] = transaction_json.get('$tx').get('$i')
                if '$o' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$o'] = transaction_json.get('$tx').get('$o')
                if '$r' in transaction_json.get('$tx'):
                    self.transaction.get('$tx')['$r'] = transaction_json.get('$tx').get('$r')
                self.transaction['$selfsign'] = transaction_json.get('$selfsign')
                self.transaction['$sigs'] = transaction_json.get('$sigs')
            except:
                raise Exception('transaction information incomplete')




        
    


