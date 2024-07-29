import json

with open('discoverytiles.json', 'r') as file:
    data = json.load(file)

print(data)