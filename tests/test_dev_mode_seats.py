"""Dev mode lets a tester drive the active player, but never rewrites their own seat."""
import config
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import players, reload

P1, P2 = 1, 2


def test_update_player_refuses_another_factions_seat(make_game):
    game = make_game({"players": players("blue", "red")})
    blue = game.getPlayerObjectFromColor("blue")
    blue["science"] = 9

    game.update_player(PlayerHelper(str(P2), blue))  # a tester's seat id holding blue's stats

    assert game.gamestate["players"][str(P2)]["color"] == "red"
    assert game.gamestate["players"][str(P2)]["science"] != 9


def test_tester_pressing_for_the_active_player_keeps_their_own_seat(start_game, press, monkeypatch):
    game, channel = start_game()
    monkeypatch.setattr(config, "dev_mode", True)
    monkeypatch.setattr(config, "tester_ids", {str(P2)})

    press(channel, P2, "permanentlyPass")  # red's id, blue's turn

    state = reload(game).gamestate
    assert state["players"][str(P2)]["color"] == "red"
    assert state["players"][str(P1)]["perma_passed"] is True
