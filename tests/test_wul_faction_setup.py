from Buttons.Draft import DraftButtons
from helpers.GamestateHelper import GamestateHelper
from setup.GameInit import GameInit
from tests.fakes import FakeChannel, FakeInteraction, buttons, reload


def test_setup_loads_the_wulfen_blueprints(start_game, press):
    game, channel = start_game(factions=["wul", "eri"])

    press(channel, 1, "FCIDblue_startUpgrade")
    labels = list(buttons(channel).values())
    assert "Interceptor" not in labels
    state = reload(game)
    player = state.get_player(1)
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "252"
    assert tile["money_pop"] == [1] and tile["material_pop"] == [1]
    assert tile["materialadv_pop"] == [0]
    assert tile["player_ships"] == ["blue-cru"]
    assert player["home_planet"] == "252"
    assert player["grid_tech"] == ["fus"]
    assert "interceptor_parts" not in player
    assert player["cruiser_parts"] == ["nus", "hul", "nud", "ioc", "ioc"]
    assert player["dread_parts"] == ["elc", "nus", "nud", "empty", "hul", "hul", "ioc", "ioc"]
    assert player["starbase_parts"] == ["empty", "hul", "hul", "ioc", "ioc"]


def test_general_setup_gives_two_brown_factions_different_colours(games_dir, run):
    GameInit("Two brown factions", [[1, "<@1>"], [2, "<@2>"]], "def", True, True, False, False,
             community_factions=True).create_game()
    game = GamestateHelper(None, "aeb1")
    game.setup_techs_and_outer_rim(2, False, False)
    channel = FakeChannel("aeb1-actions")
    interaction = FakeInteraction(channel, role_names=["aeb1"])

    run(DraftButtons.generalSetup(interaction, game, [1, 2], ["wul", "rho"]))

    state = reload(game).gamestate
    assert state["players"]["1"]["color"] == "brown"
    assert state["players"]["2"]["color"] != "brown"
