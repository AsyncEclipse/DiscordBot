from types import SimpleNamespace

import pytest

from Buttons.Move import MoveButtons
from Buttons.Pulsar import PulsarButtons
from tests.fakes import FakeInteraction, buttons, player_helper, reload


@pytest.fixture
def moving_ships(start_game, monkeypatch):
    monkeypatch.setattr("Buttons.Move.DrawHelper", lambda *args, **kwargs: SimpleNamespace(
        mergeLocationsFile=lambda *args: None, board_tile_image_file=lambda *args: None))
    game, channel = start_game()
    game.add_tile("301", 0, "202")
    game.get_player(1)["move_apt"] = 3
    game.gamestate["board"]["201"]["player_ships"] = ["blue-int"] * 3
    game.gamestate["board"]["201"]["currentAction"] = "upgrade"
    game.update()
    return game, channel


@pytest.mark.parametrize("kind, count", [("normal", 1), ("reaction", 1), ("pulsar", 8)])
def test_move_selection_respects_action_limit(moving_ships, press, run, kind, count):
    game, channel = moving_ships
    player = game.get_player(1)
    player["passed"] = kind == "reaction"
    game.update()
    if kind == "pulsar":
        run(PulsarButtons.pulsarAction(game, player, FakeInteraction(channel),
                                      player_helper(game, "blue"), "pulsarAction_201_move"))
    else:
        press(channel, 1, "FCIDblue_startMove")
    press(channel, 1, f"FCIDblue_moveFrom_201_{count}")
    selection = press(channel, 1, f"FCIDblue_moveThisShip_201_interceptor_{count}_all")
    if kind == "normal":
        assert selection.message.edited["view"].children[0].label == "Add Interceptor (1/3)"
        added = press(channel, 1, "FCIDblue_moveQueueAdd_201_interceptor_1_1_all",
                      message=selection.message)
        assert added.message.edited["view"].children[0].label == "Add Interceptor (2/3)"
        press(channel, 1, "FCIDblue_moveQueueDone_201_interceptor_1_2_all", message=selection.message)
    else:
        assert not hasattr(selection.message, "edited")
    destination = next(cid for cid in buttons(channel)
                       if cid.startswith("FCIDblue_moveTo_201_interceptor_301_"))
    press(channel, 1, destination)
    continuation = next((cid for cid in buttons(channel) if "moveQueueContinue" in cid), None)
    if kind == "normal":
        assert continuation
        press(channel, 1, continuation)
    else:
        assert not continuation
        assert not any("startMove" in cid for cid in buttons(channel))
    assert reload(game).gamestate["board"]["301"]["player_ships"].count("blue-int") == (
        2 if kind == "normal" else 1)


def test_reaction_rejects_a_stale_multi_ship_selection(moving_ships, run):
    game, channel = moving_ships
    player = game.get_player(1)
    player["passed"] = True
    interaction = FakeInteraction(channel)

    run(MoveButtons.moveQueueDone(game, player, interaction,
                                 "moveQueueDone_201_interceptor_1_2_all"))

    assert "no longer move" in interaction.followup.sent[0][0]
    assert game.gamestate["board"]["201"]["player_ships"].count("blue-int") == 3


@pytest.mark.parametrize("passed, count", [(True, 2), (False, 4), (False, 9)])
def test_queue_continuation_rechecks_activations(moving_ships, run, passed, count):
    game, channel = moving_ships
    player = game.get_player(1)
    player["passed"] = passed
    interaction = FakeInteraction(channel)

    run(MoveButtons.sendMoveContinuation(player, interaction, count - 1, 1,
                                         "201", "interceptor", "_all", "301", "301"))
    assert not any("moveQueueContinue" in cid for cid in buttons(channel))
    run(MoveButtons.moveQueueContinue(game, player, interaction,
                                     f"moveQueueContinue_201_interceptor_301_{count}_1_all",
                                     player_helper(game, "blue")))

    assert game.gamestate["board"]["201"]["player_ships"].count("blue-int") == 3
    assert any("No move activations remain" in (content or "") for content, kwargs in channel.sent)
