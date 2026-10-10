import json

import config
from setup.GameInit import GameInit


def test_game_init_uses_provided_player_names(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "gamestate_path", str(tmp_path))
    monkeypatch.setattr(config, "game_number", 1)
    monkeypatch.setattr("setup.GameInit.update_game_number", lambda: None)

    GameInit("T", [[1, "<@1>"], [90000, "<@42>"]], "def", True, True, False, False).create_game()

    with open(tmp_path / "aeb1.json") as f:
        gamestate = json.load(f)
    assert gamestate["players"]["1"]["player_name"] == "<@1>"
    assert gamestate["players"]["90000"]["player_name"] == "<@42>"
