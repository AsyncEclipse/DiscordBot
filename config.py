import json

with open("config.json", "r") as f:
    data = json.load(f)
    token = data["token"]
    game_number = data["game_number"]
    gamestate_path = data["gamestate_path"]
    f.close()

def update_game_number():
    with open("config.json", "w") as f:
        data["game_number"] += 1
        json.dump(data, f)

