from ActiveLedgerSDK import onboard


user = onboard.createIdentity('Jialin_test2')

# print(type(user))

user.generate_key('rsa', 2048)
# user.export_key()
user.setHTTP('http://testnet-uk.activeledger.io:5260')

# print(user.key_type)

res = onboard.onboardIdentity(user)

print(res)

print(type(res))