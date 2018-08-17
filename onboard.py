from ActiveLedgerSDK import onboard
import json



user = onboard.createIdentity('Jialin_test2')

# print(type(user))

user.generate_key('rsa', 2048)
user.export_key()
user.setHTTP('http://testnet-uk.activeledger.io:5260')

# print(user.key_type)

res = onboard.onboardIdentity(user)

print(res)


# print(json.dumps(res, indent=2))

# user.setStreamID(res)
# user.streamID


# print(user.streamID)


# print(res.get('$streams').get('new')[0].get('id'))

