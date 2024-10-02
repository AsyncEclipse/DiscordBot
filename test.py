import json

with open("data/techs.json", "r") as f:
    data = json.load(f)

lister = []
for i in data:
    lister.append(i)


lister.sort()
print(lister)