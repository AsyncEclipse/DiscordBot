"""A Pulsar sector's free Move action.

A Pulsar lets its owner take a free Move action: one ship moves, no move activation
is spent and no influence disc is paid. Reported from the official server: pressing
"Do Pulsar Move" offered no ships at all and said the player had 0 activations left.
"""
from tests.fakes import buttons, reload


def pulsar_game(start_game):
    game, channel = start_game(factions=["atl", "eri"])
    game.add_tile("301", 0, "202")
    game.gamestate["board"]["201"].update({"type": "pulsar", "currentAction": "upgrade"})
    game.update()
    return game, channel


def test_pulsar_move_offers_a_ship_to_move(start_game, press):
    game, channel = pulsar_game(start_game)

    press(channel, 1, "FCIDblue_pulsarAction_201_move")

    assert "FCIDblue_moveFrom_201_8" in buttons(channel)


def test_pulsar_move_moves_one_ship_for_free(start_game, press):
    game, channel = pulsar_game(start_game)
    discs = game.get_player(1)["influence_discs"]

    press(channel, 1, "FCIDblue_pulsarAction_201_move")
    press(channel, 1, "FCIDblue_moveFrom_201_8")
    press(channel, 1, "FCIDblue_moveThisShip_201_interceptor_8_all")
    press(channel, 1, next(cid for cid in buttons(channel)
                           if cid.startswith("FCIDblue_moveTo_201_interceptor_301_8")))

    state = reload(game)
    assert state.gamestate["board"]["301"]["player_ships"] == ["blue-int"]
    assert state.get_player(1)["influence_discs"] == discs
    # A free move is not a Move action, so it neither opens a second ship nor an extra activation.
    assert not any("startMove" in cid or "moveFrom" in cid for cid in buttons(channel))
