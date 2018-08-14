'''
python onboarding function 

include 

1. user create 
2. export keys
3. import keys
4. post http hit

'''

from pythonSDK.primitives import identity


user = identity.identity('username2')

user.generate_key('rsa',2048)

user.export_key()



