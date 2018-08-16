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
    
    def import_ior(self, **kwargs):
        '''
        import i, o, r from file 
        the default path is in sdk-contracts folder
        i, o, r = 'filename'
        '''
        # pass default value None 
        i = kwargs.get('i', None)
        o = kwargs.get('o', None)
        r = kwargs.get('r', None)
        try:
            if i is not None:
                f1 = open('./sdk-keypairs/{}'.format(i), 'r')
                ii = f1.read()
                self.transaction.get('$tx')['$i'] = ii
                f1.close
            if o is not None:
                f2 = open('./sdk-keypairs/{}'.format(o), 'r')
                oo = f2.read()
                self.transaction.get('$tx')['$o'] = oo
            if r is not None:
                f3 = open('./sdk-keypairs/{}'.format(r), 'r')
                rr = f3.read()
                self.transaction.get('$tx')['$r'] = rr
        except:
            raise Exception('key pair file(s) not exist')


        filename = kwargs.get('name', None)

        
    


