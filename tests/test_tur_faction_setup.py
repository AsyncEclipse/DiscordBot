import random

from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, reload

def test_setup_gives_turtugan_its_home_ships_and_reserve(start_game):
    game, _channel = start_game(factions=["tur", "eri"])
    player = game.get_player(1)
    assert player["name"] == "Turtugan"
    assert player["color"] == "blue"
    assert player["home_planet"] == "253"
    assert player["military_tech"] == ["stb"]
    assert player["reputation_track"] == ["rep", "mixed", "mixed", "mixed"]
    assert (player["materials"], player["science"], player["money"]) == (4, 3, 3)
    assert player["move_apt"] == 2
    assert player["ship_stock"] == [8, 4, 2, 3]
    assert game.gamestate["board"]["201"]["player_ships"] == ["blue-sb"]
    tile = game.gamestate["board"]["201"]
    assert tile["sector"] == "253"
    assert tile["scienceadv_pop"] == [0] and tile["materialadv_pop"] == [0]
    assert tile["money_pop"] == [1] and tile["material_pop"] == [1]
    reserve = player["deep_space_sectors"]
    assert len(reserve) == 2
    assert all(tile.isdigit() for tile in reserve)
    assert "Deep Space reserve: 2 hidden S3 sectors" in game.displayPlayerStats(player)
    assert all(tile not in game.displayPlayerStats(player) for tile in reserve)


def test_only_turtugan_gets_a_deep_space_reserve(start_game):
    game, _channel = start_game(factions=["eri", "hyd"])
    assert "deep_space_sectors" not in game.get_player(1)


def test_general_setup_posts_the_reserved_sectors(games_dir, run):
    random.seed(0)
    GameInit("T", [[1, "<@1>"], [2, "<@2>"]], "def", True, True, False, False).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])
    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["tur", "eri"]))

    state = reload(game)
    reserve = state.get_player(1)["deep_space_sectors"]
    assert state.get_player(1)["color"] == "teal"
    assert len(reserve) == 2
    messages = [content for content, _ in channel.sent if content]
    reserve_messages = [content for content in messages if "Deep Space Explorers reserves" in content]
    assert len(reserve_messages) == 1
    assert "2 hidden S3 sectors" in reserve_messages[0]
    assert all(tile not in reserve_messages[0] for tile in reserve)
    assert all(not kwargs for content, kwargs in channel.sent if content in reserve_messages)
    assert state.gamestate["board"]["201"]["sector"] == "253"
