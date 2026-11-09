"""Soul-Hunters: one live soul per enemy sector whose player population the Wraith destroys."""

from Buttons.Influence import InfluenceButtons
from helpers.CombatHelper import Combat
from helpers.DrawHelper import DrawHelper
from helpers.PlayerHelper import PlayerHelper
from tests.fakes import FakeInteraction, board_tile, player_stats, reload


def soul_game(make_game, money_pop=(1, 1), science_pop=(), owner="red", game_id="t"):
    blue = player_stats("wra", color="blue")
    red = player_stats("hyd", color="red")
    red["owned_tiles"] = ["101"]
    game = make_game({"player_count": 2, "players": {"1": blue, "2": red},
                      "board": board_tile(["blue-int"], owner=owner, sector=101,
                                          money_pop=list(money_pop),
                                          science_pop=list(science_pop)),
                      "advanced_ai": False, "wa_ai": False}, game_id=game_id)
    return game


def test_orbital_population_counts_as_enemy_population(make_game):
    blue = player_stats("wra", color="blue")
    tile = {"owner": "red", "money_pop": [0], "orbital_pop": [1]}

    assert PlayerHelper.capture_wraith_soul(blue, tile, last_cube=True) is False
    assert PlayerHelper.capture_wraith_soul(blue, tile, last_cube=False) is True


def test_killing_an_orbital_population_captures_a_soul(make_game, run):
    game = soul_game(make_game, money_pop=())
    game.gamestate["board"]["101"]["orbital_pop"] = [1]
    game.update()
    blue = game.getPlayerObjectFromColor("blue")

    run(Combat.killPop(game, "killPop_101_orbital_0", FakeInteraction(), blue))

    assert reload(game).get_player(1)["wraithSouls"] == 1


def test_one_soul_for_the_last_enemy_player_cube(make_game, run):
    game = soul_game(make_game)
    blue = game.getPlayerObjectFromColor("blue")

    run(Combat.killPop(game, "killPop_101_money_0", FakeInteraction(), blue))
    assert reload(game).get_player(1).get("wraithSouls", 0) == 0

    run(Combat.killPop(game, "killPop_101_money_0", FakeInteraction(),
                       reload(game).get_player(1)))
    state = reload(game)
    assert state.get_player(1)["wraithSouls"] == 1
    assert DrawHelper(state.gamestate).get_public_points(state.get_player(1), False) == 1


def test_destroy_all_counts_once_per_sector_not_once_per_cube(make_game, run):
    game = soul_game(make_game, money_pop=(1, 1), science_pop=(1,))
    blue = game.getPlayerObjectFromColor("blue")

    run(InfluenceButtons.removeInfluenceFinish(
        game, FakeInteraction(), "removeInfluenceFinish_101_graveYard", True, blue))

    assert reload(game).get_player(1).get("wraithSouls") == 1


def test_neutral_and_own_cubes_do_not_count(make_game, run):
    neutral = soul_game(make_game, money_pop=(), owner="red", game_id="n")
    neutral.gamestate["board"]["101"]["neutral_pop"] = [1]
    neutral.update()
    run(Combat.killPop(neutral, "killPop_101_neutral_0", FakeInteraction(),
                       neutral.getPlayerObjectFromColor("blue")))
    assert reload(neutral).get_player(1).get("wraithSouls", 0) == 0

    own = soul_game(make_game, owner="blue", game_id="o")
    own.get_player(1)["owned_tiles"].append("101")
    own.update()
    run(Combat.killPop(own, "killPop_101_money_0", FakeInteraction(),
                       own.getPlayerObjectFromColor("blue")))
    assert reload(own).get_player(1).get("wraithSouls", 0) == 0


def test_normal_influence_removal_does_not_count(make_game, run):
    game = soul_game(make_game)
    blue = game.getPlayerObjectFromColor("blue")

    run(InfluenceButtons.removeInfluenceFinish(
        game, FakeInteraction(), "removeInfluenceFinish_101_normal", True, blue))

    assert reload(game).get_player(1).get("wraithSouls", 0) == 0


def test_a_soul_survives_losing_the_sector_and_repopulation_can_be_destroyed_again(make_game, run):
    game = soul_game(make_game)
    blue = game.getPlayerObjectFromColor("blue")
    run(Combat.killPop(game, "killPop_101_money_0", FakeInteraction(), blue))
    run(Combat.killPop(game, "killPop_101_money_0", FakeInteraction(),
                       reload(game).get_player(1)))
    assert reload(game).get_player(1)["wraithSouls"] == 1

    state = reload(game)
    state.gamestate["board"]["101"]["owner"] = 0
    state.update()
    assert DrawHelper(state.gamestate).get_public_points(state.get_player(1), False) == 1

    state.gamestate["board"]["101"]["owner"] = "red"
    state.gamestate["board"]["101"]["money_pop"] = [1]
    state.gamestate["players"]["2"]["owned_tiles"].append("101")
    state.update()
    run(Combat.killPop(state, "killPop_101_money_0", FakeInteraction(),
                       state.getPlayerObjectFromColor("blue")))
    assert reload(state).get_player(1)["wraithSouls"] == 2


def test_old_saves_without_the_counter_score_zero():
    player = player_stats("wra", color="blue")
    player.pop("wraithSouls")
    assert DrawHelper({"board": {}}).get_public_points(player, False) == 0


def test_display_player_stats_reports_the_souls(make_game):
    game = soul_game(make_game)
    player = game.getPlayerObjectFromColor("blue")
    player["wraithSouls"] = 2

    text = game.displayPlayerStats(player)

    assert "Souls captured: 2 (+2 offboard power, +2 VP)" in text
