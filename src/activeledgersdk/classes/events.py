from sseclient import SSEClient


class Events(object):

    def subscribe(self,host,port):
        messages = SSEClient("http://"+host+":"+port+"/api/activity/subscribe")
        print("msg")
        for msg in messages:
            print(msg)
        return messages


    def subscribeStream(self,host,port,stream):
        messages = SSEClient("http://"+host+":"+port+"/api/activity/subscribe/"+stream)
        return messages


    def contractEventSubscribe(self,host,port,contract,event):
        messages = SSEClient("http://"+host+":"+port+"/api/events/"+contract+"/"+event)
        return messages


    def contractSubscribe(self,host,port,contract):
        messages = SSEClient("http://"+host+":"+port+"/api/events"+contract)
        return messages


    def eventsubscribe(self,host,port):
        messages = SSEClient("http://"+host+":"+port+"/api/events")
        return messages