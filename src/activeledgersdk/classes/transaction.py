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
    
    def import_transaction(self, transaction_object):
        '''
        import transaction object directly, user should build 
        the object according to activeldger documentation 
        '''
        if transaction_object is not dict:
            raise Exception('transaction object must be a dictionary')
        else:
            self.transaction = transaction_object
