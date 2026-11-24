"""Legion of Midas: Midas Touch and All That Glitters."""
from Buttons.Move import MoveButtons
from Buttons.Turn import TurnButtons
from Buttons.Explore import ExploreButtons
from helpers import FactionData
from helpers.GamestateHelper import GamestateHelper
from tests.fakes import FakeInteraction, buttons, reload


def _snapshots(monkeypatch):
    calls = []
    monkeypatch.setattr(GamestateHelper, "updateSaveFile", lambda self: calls.append(1))
    return calls


def test_midas_touch_costs_one_and_adds_an_activation(start_game, run):
    game, channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    player["money"] = 10
    state.update()

    run(TurnButtons.midasTouch(player, state, FakeInteraction(channel)))
    labels = list(buttons(channel).values())
    assert "Build (+1 activation, 1 money)" in labels

    interaction = FakeInteraction(channel)
    run(TurnButtons.midasAction(player, state, interaction, "midasAction_build"))
    after = reload(game).get_player(1)
    assert after["money"] == 9
    assert after["midasBoost"] == "build"
    assert FactionData.action_apt(after, "build") == 3


def test_midas_paid_action_writes_a_turn_start_save(start_game, monkeypatch, run):
    game, channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    player["money"] = 10
    state.update()
    snapshots = _snapshots(monkeypatch)

    run(TurnButtons.midasAction(player, state, FakeInteraction(channel), "midasAction_build"))

    assert len(snapshots) == 1
    assert reload(game).get_player(1)["midasBoost"] == "build"


def test_midas_touch_can_be_cancelled_without_paying(start_game, run, press):
    game, channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    player["money"] = 10
    state.update()

    run(TurnButtons.midasTouch(player, state, FakeInteraction(channel)))
    assert "FCIDblue_midasCancel" in buttons(channel)
    press(channel, 1, "FCIDblue_midasCancel")

    assert reload(game).get_player(1)["money"] == 10
    assert any(cid.startswith("FCIDblue_startBuild") for cid in buttons(channel))


def test_midas_touch_surcharge_with_seven_or_fewer_disks(start_game, run):
    game, channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    player["influence_discs"] = 7
    player["money"] = 10
    state.update()

    run(TurnButtons.midasTouch(player, state, FakeInteraction(channel)))
    labels = list(buttons(channel).values())
    assert "Build (+1 activation, 2 money)" in labels
    assert "Research (+1 activation, 4 money)" in labels


def test_all_that_glitters_gives_one_money_for_passing_first(start_game, press):
    game, channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    player["money"] = 0
    state.update()

    press(channel, 1, "FCIDblue_passForRound")

    after = reload(game).get_player(1)
    assert after["money"] == 1
    assert after["firstPlayer"] is True


def test_second_explore_retires_the_first_finish_prompt(start_game, run, press):
    game, channel = start_game(factions=["mid", "eri"])
    game.get_player(1)["money"] = 10
    game.update()
    press(channel, 1, "FCIDblue_midasTouch")
    press(channel, 1, "FCIDblue_midasAction_explore")
    state = reload(game)
    interaction = FakeInteraction(channel)
    run(ExploreButtons.discardTile(state, interaction, state.get_player(1), "discardTile_101"))
    first_finish = state.get_player(1)["exploreFinishMessage"]
    assert first_finish not in channel.deleted
    press(channel, 1, "FCIDblue_startExplore2")
    assert first_finish in channel.deleted
    state = reload(game)
    run(ExploreButtons.discardTile(state, interaction, state.get_player(1), "discardTile_102"))
    finish_prompts = [message.id for (content, kwargs), message in zip(channel.sent, channel.messages)
                      if any(item.custom_id == "FCIDblue_finishAction"
                             for item in getattr(kwargs.get("view"), "children", []))
                      and message.id not in channel.deleted]
    assert len(finish_prompts) == 1


def test_paid_third_move_opens_the_ship_selection(start_game, press, run):
    game, channel = start_game(factions=["mid", "eri"])
    player = game.get_player(1)
    player["midasBoost"] = "move"
    game.update()

    run(MoveButtons.sendMoveContinuation(game, player, FakeInteraction(channel), 2))
    assert "(1 left)" in channel.sent[-1][0]
    press(channel, 1, "FCIDblue_startMove_3")

    assert "FCIDblue_moveFrom_201_3" in buttons(channel)
