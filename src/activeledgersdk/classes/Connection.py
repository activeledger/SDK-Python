class Connection(object):

    def __init__(self):
        '''
        Connection Parameters
        '''
        self.protocol=None
        self.url=None
        self.port=None


    def getProtocol(self): 
	    return self.protocol
	

    def setProtocol(self, protocol):
	    self.protocol = protocol
	

    def getUrl(self):
	    return self.url
	

    def setUrl(self, url):
	    self.url = url
	

    def getPort(self):
	    return self.port
	

    def setPort(self, port): 
	    self.port = port
	

    def getConnectionURL(self):
	    return self.getProtocol() + "://" + self.getUrl() + ":" + self.getPort()
            

    def setConnection(self,protocol, url, port):

	    self.setProtocol(protocol)
	    self.setUrl(url)
	    self.setPort(port)

	