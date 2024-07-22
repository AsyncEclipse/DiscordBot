import json

with open("ActiveGames/aeb50.json", "r") as f:
    tester = json.load(f)

print(len(tester["available_techs"]))