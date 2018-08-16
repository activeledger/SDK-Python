a = {
    '$tx': {
        '$namespace': None, 
        '$contract': None,
        '$entry': None,
        '$i': 2,
        '$o': None,
        '$r': None,
    },
    '$selfsign': None,
    '$sigs': None,
}

print(a.get('$tx').get('$i'))
a.get('$tx')['$i'] = 4
print(a.get('$tx').get('$i'))