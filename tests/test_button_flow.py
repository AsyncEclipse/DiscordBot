"""Integration tests: press real buttons through ButtonListener.resolveButton."""
import os

from Buttons.Build import BuildButtons
from Buttons.Move import MoveButtons
from tests.fakes import FakeInteraction, buttons, player_helper, player_stats, reload

P1, P2 = 1, 2


def test_pass_then_next_player_gets_turn(start_game, press):
    game, channel = start_game()
    blue_money = game.get_player(P1)["money"]
    red_money = game.get_player(P2)["money"]
    press(channel, P1, "FCIDblue_passForRound")
    state = reload(game).gamestate
    assert state["players"][str(P1)]["passed"]
    assert state["players"][str(P1)]["money"] == blue_money + 2
    assert state["activePlayerColor"] == ["red"]
    assert any(l and "Build" in l for l in buttons(channel).values())
    # a second press in the same process must not be blocked by the first one's lock
    press(channel, P2, "FCIDred_passForRound")
    red = reload(game).get_player(P2)
    assert red["passed"]
    assert red["money"] == red_money


def _saves(monkeypatch):
    """Every completed save of the game file."""
    saves = []
    replace = os.replace

    def record(source, destination):
        saves.append(destination)
        replace(source, destination)

    monkeypatch.setattr(os, "replace", record)
    return saves


def test_starting_a_build_saves_a_plain_faction_once(make_game, monkeypatch, run):
    game = make_game({"players": {"1": player_stats("hyd", color="blue")}, "board": {}})
    saves = _saves(monkeypatch)
    run(BuildButtons.startBuild(game, game.getPlayerObjectFromColor("blue"), FakeInteraction(),
                                "startBuild", player_helper(game, "blue")))
    assert len(saves) == 1


def test_start_build_clears_the_cog_extra_upgrade_without_saving_twice(make_game, monkeypatch, run):
    game = make_game({"players": {"1": player_stats("cog", color="blue",
                                                    infinitePossibilitiesUsed=True)}, "board": {}})
    saves = _saves(monkeypatch)
    run(BuildButtons.startBuild(game, game.getPlayerObjectFromColor("blue"), FakeInteraction(),
                                "startBuild", player_helper(game, "blue")))
    assert len(saves) == 1
    assert "infinitePossibilitiesUsed" not in game.get_player(P1)


def test_start_move_saves_only_when_it_resets_something(make_game, monkeypatch, run):
    game = make_game({"players": {"1": player_stats("hyd", color="blue")}, "board": {}})
    saves = _saves(monkeypatch)
    run(MoveButtons.startMove(game, game.getPlayerObjectFromColor("blue"), FakeInteraction(),
                              "startMove", False))
    assert saves == []


def test_start_move_saves_the_cog_reset(make_game, monkeypatch, run):
    game = make_game({"players": {"1": player_stats("cog", color="blue",
                                                    infinitePossibilitiesUsed=True)}, "board": {}})
    saves = _saves(monkeypatch)
    run(MoveButtons.startMove(game, game.getPlayerObjectFromColor("blue"), FakeInteraction(),
                              "startMove", False))
    assert len(saves) == 1
    assert "infinitePossibilitiesUsed" not in game.get_player(P1)
def test_a_build_action_can_end_without_building_anything(start_game, press):
    game, channel = start_game(factions=["hyd", "eri"])
    press(channel, P1, "FCIDblue_startBuild")
    press(channel, P1, "FCIDblue_buildIn_201")

    assert "FCIDblue_finishAction" in buttons(channel)
    press(channel, P1, "FCIDblue_finishAction")

    assert "FCIDblue_endTurn" in buttons(channel)


def test_put_down_population_can_be_declined(start_game, run):
    from Buttons.Population import PopulationButtons

    game, channel = start_game(factions=["hyd", "eri"])
    player = game.get_player(P1)
    run(PopulationButtons.startPopDrop(game, player, FakeInteraction(channel)))
    assert any(cid.endswith("_declinePopDrop") for cid in buttons(channel))

    message = channel.message_with("FCIDblue_declinePopDrop")
    run(PopulationButtons.declinePopDrop(game, player, FakeInteraction(channel, message=message)))
    assert message.id in channel.deleted


def test_cancelled_pulsar_build_does_not_limit_next_build(start_game, press):
    game, channel = start_game()
    game.get_player(1)["pulsarBuild"] = True
    game.update()
    press(channel, 1, "FCIDblue_startBuild2")
    press(channel, 1, "FCIDblue_buildIn_201")
    press(channel, 1, "FCIDblue_finishAction")
    assert not reload(game).get_player(1).get("pulsarBuild")
