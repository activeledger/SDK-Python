import json
import requests
from activeledgerPythonSDK.classes import Connection as con

class ActivityStreams(object):
 

    def getActivityStreams(self,host,ids):
        '''
        GetActivityStreams returns list of streams with ids sent in request
        
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.post(host+"/api/stream",data=json.dumps(ids),headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("streams")


    def getActivityStream(self,host,id):
        '''
       GetActivityStream returns a single stream with id sent in request
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(host+"/api/stream/"+id,headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("stream")


    def getActivityStreamVolatile(self,host,id):
        '''
        GetActivityStreamVolatile returns stream volatile
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(host+"/api/stream/"+id+"/volatile",headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("stream")


    def setActivityStreamVolatile(self,host,id,body):
        '''
        Sets stream volatile
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.post(host+"/api/stream/"+id+"/volatile",data=json.dumps(body),headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("stream")

    def getActivityStreamChanges(self,host):
        '''
        Gets changes in all streams
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(host+"/api/stream/changes",headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("changes")



    def searchActivityStreamPost(self,host,query):
        '''
        search stream with query object
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.post(host+"/api/stream/search",data=json.dumps(query),headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        
        return res.get("stream")


    def searchActivityStreamGet(self,host,query):
        '''
        search stream with query string
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(host+"/api/stream/search?sql="+query,headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        print (res)
        return res.get("stream")


    def findTransaction(self,host,umid):
        '''
        Find Transaction using umid
        '''
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(host+"/api/tx/"+umid,headers = message_header, timeout = 10)
        except:
            raise Exception('Http timeout')
        res =json.loads(r.content.decode())
        
        print (res)
        return res.get("stream")