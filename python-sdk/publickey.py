# from cryptography.hazmat.primitives.asymmetric import rsa

import os


# RSA module from Crypto
from Crypto.PublicKey import RSA





# write a function to generate rsa keys
def generate_rsa_keys(number):
    pubkey = RSA.generate(number)
    prvkey = RSA.generate(number)


    a = pubkey.exportKey()
    

f = open('a.pem', 'wb')

f.write(a)


    print(pubkey.exportKey(format='PEM'))
    # return pubkey, prvkey

    # pubf = open('pubkey.pem','w')
    # prvf = open('prvkey.pem','w')
    # pubkey.exportKey('pubkey.pem')
    # prvkey.exportKey('prvkey.pem')


   

    # while not (os.path.isfile('pubkey.prem') or os.path.isfile('prvkey.prem')):
    #     try:
    #         pubf = open('pubkey.pem','w')
    #         prvf = open('prvkey.pem','w')
    #         pubf.write(pubkey.exportKey('PEM'))
    #         prvf.write(prvkey.exportKey('PEM'))
    #         pubf.close
    #         prvf.close
    #         break
    #     except:
    #         print('Key certificates with same name exist!')


generate_rsa_keys(1024)




        