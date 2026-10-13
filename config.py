import json
import random


with open("config.json", "r") as f:
    data = json.load(f)

token = data["token"]
game_number = data["game_number"]
gamestate_path = data["gamestate_path"]

# Optional dev/testing keys in config.json. dev_mode lets configured testers
# drive every player; guild_id scopes slash-command sync to one guild;
# dev_seed makes RNG reproducible.
dev_mode = data.get("dev_mode", False)
tester_ids = data.get("tester_ids", data.get("tester_id", []))
if not isinstance(tester_ids, list):
    tester_ids = [tester_ids]
tester_ids = {str(tester_id) for tester_id in tester_ids}
guild_id = data.get("guild_id", 0)
if data.get("dev_seed") is not None:
    random.seed(data["dev_seed"])


def is_tester(player_id):
    return str(player_id) in tester_ids


def update_game_number():
    with open("config.json", "w") as f:
        data["game_number"] += 1
        json.dump(data, f)
