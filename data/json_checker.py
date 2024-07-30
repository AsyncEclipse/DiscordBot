import json

with open('sectors.json', 'r') as file:
    data = json.load(file)

print(data)