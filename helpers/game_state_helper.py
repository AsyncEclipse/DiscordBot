import json
import os
import config

def read(game_id):

    with open(f"{config.gamestate_path}/{game_id}.json", "r") as f:
        gamestate = json.load(f)

    return gamestate

def write(game_id, gamestate):

    with open(f"{config.gamestate_path}/{game_id}.json", "w") as f:
        json.dump(gamestate, f)
