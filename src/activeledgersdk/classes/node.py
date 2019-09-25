import json
import requests
from activeledgersdk.classes import Connection as con

class Node(object):
 

    def getNodeRefs(self):
        '''
        Get node references for tertoriallity
        returns node ids which are online
        '''
        List=[]
        message_header = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        try:
            r = requests.get(con.Connection.getUrl+"/a/status",headers = message_header, timeout = 10)
        except:
            raise Exception('Http post timeout')
        res =json.loads(r.content.decode())
        nodes = res.get('neighbourhood').get('neigbours')
        for node in nodes:
           
            for attribute, value in node.items():
                if value.get("isHome"):
                    List.append(attribute)

        
        return List